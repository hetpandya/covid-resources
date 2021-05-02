import os
from flask import Flask,render_template,session,redirect
from flask import request,jsonify
import base64
import json
from datetime import datetime
from pytz import timezone
from models import *
import random
from twilio.rest import Client

app = Flask(__name__)

root = os.getcwd()

try:
    with open(os.path.join(root,"state_data.json")) as json_file:
        states_data = json.load(json_file)
except:
    with open(os.path.join(root,"/home/hetpandy/public_html/flask/state_data.json")) as json_file:
	    states_data = json.load(json_file)

states_data = states_data["states"]
services_indices = ["remdesivir","hospital-beds","plasma","oxygen","tiffins","fabiflu","private-vehicle","icu-beds","tocilizumab","ventilators"]
blood_groups = "A+, A-, B+, B-, O+, O-, AB+, AB-".split(",")
blood_groups = [group.strip() for group in blood_groups]
state_names = [(ix+1,state["name"]) for ix,state in enumerate(states_data)]
date_format = '%d-%m-%Y'
twilio_client = Client(creds["twilio_sid"], creds["twilio_token"])

@app.route('/get-city/<id>', methods=["POST"])
def get_city(id):
      if request.method == "POST":
        return jsonify(states_data[int(id)-1]["districts"]),200

@app.route('/search-resources', methods=["POST"])
def search_resources():
    if request.method == "POST":
        data = request.get_json()
        city_id = int(data["city_id"])
        state_id = int(data["state_id"])
        other_cities = int(data["other_cities"])

        responses = {}
        if len(data["resources"]) > 0:
            req_res = data["resources"][0]
            response = []

            if other_cities == 1:
                db_query = db_session.query(Resources).order_by(Resources.last_updated.desc()).filter_by(state_id = state_id,
                                                                resource_type=int(req_res),
                                                                donor_or_recipient=0,
                                                                is_approved_by_admin=1).all()
            else:
                db_query = db_session.query(Resources).order_by(Resources.last_updated.desc()).filter_by(state_id = state_id,
                                                                city_id = city_id,
                                                                resource_type=int(req_res),
                                                                donor_or_recipient=0,is_approved_by_admin=1).all()
            for resource in db_query:
                if resource.available_donors != []:
                    donor = resource.available_donors[0]

                    location = states_data[state_id - 1]["districts"][resource.city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]
            
                    contact = [contact+"<br>".replace(",","") for contact in donor.contact.split(",")]
                    address = f"<br><b>Address:</b> {donor.address.strip()}" if donor.address != "" else ""
                    additional_information = f"<br><b>Additional Information:</b> {resource.additional_information}" if resource.additional_information and resource.additional_information != "" else ""
                    
                    resp_dict = {"name":donor.name + address + additional_information,
                                "resource_id":resource.id,
                                'contact':contact,
                                'location':location,
                                "available":"Yes" if resource.available else "No",
                                "count":resource.resource_count,
                                "verified":"Yes" if resource.verified else "No",
                                "last_updated":resource.last_updated.strftime(date_format) if resource.last_updated else ""}

                    if int(req_res) == 2:
                        resp_dict["blood_group"] = donor.blood_group
                    response.append(resp_dict)
            responses[services_indices[int(req_res)]] = response
        return responses,200  

@app.route('/updates', methods=['GET'])
def updates():
    return render_template("updates.html")  

@app.route('/', methods=['GET'])
def index():
    return render_template("index.html",state_names = state_names,services_indices=services_indices)  

@app.route('/add-data', methods=['GET',"POST"])
def add_data():
    if request.method == "POST":
        data = request.get_json()["data"]
        state_id = int(data["states-select"]) 
        city_id = int(data["city-select"])
        name = data["donor-name"].strip()
        contact = data["donor-contact"].strip()
        resource_type = int(data["service"])
        address = data["resource-address"].strip().capitalize()
        additional_information = data["resource-info"].strip().capitalize()
        location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]
   
        if data.get("resource-count"):
            resource_count = int(data['resource-count'])
        else:
            resource_count = ""

        if data.get("verification-check"):
            verified = int(data["verification-check"])
        else:
            verified = 0

        if data.get("blood-group"):
            blood_group = data["blood-group"]
        else:
            blood_group = ""

        last_updated = ""
        if data.get("update-verification-check"):
            if int(data["update-verification-check"]) == 1:
                last_updated = datetime.now(timezone('Asia/Kolkata'))
            elif int(data["update-verification-check"]) == 0:
                if data.get("last-updated"):
                    date_str = data["last-updated"]
                    last_updated = datetime.strptime(date_str,date_format).astimezone(timezone('Asia/Kolkata'))
                else:
                    last_updated = ""
        else:
            last_updated = ""
                
        try:
            resource = {
                "resource_type":resource_type,
                "available":1,
                'verified':verified,
                "state_id":state_id,
                "city_id":city_id,
                'resource_count':resource_count,
                "is_approved_by_admin":1,
                "donor_or_recipient":0,
                "additional_information":additional_information,
                'last_updated' : last_updated}
            
            new_resource = Resources(**resource)
            db_session.add(new_resource)
            db_session.commit()
            
            donor = {"name":name,"contact":contact,"blood_group":blood_group,"resource_id":new_resource.id,"address":address}

            new_donor = Donors(**donor)
            db_session.add(new_donor)
            db_session.commit()

            join_data = db_session.query(Resources, Recipients).filter(Resources.resource_type == resource_type,Recipients.resource_id==Resources.id,Resources.state_id==state_id,Recipients.receive_notifications==1).all()

            message = f"{services_indices[resource_type].replace('-',' ').title()} Resources:\n"
            message += f"Name:{name} \n{address}({location})".strip()
            message += f"\nContact:{contact}"
            if resource_type == 2:
                message += f"\nBlood group:{blood_group}"
            verified_msg = "Yes" if verified == 1 else "No"
            message += f"\nVerified:{verified_msg}"
            message += f"\nCount:{resource_count}\n" if resource_count != "" else "".strip()
            message += f"\nOther Info:{additional_information}".strip() if additional_information != "" else "".strip()
            message += f"\nUpdated: {last_updated.strftime(date_format)}" if last_updated != "" else "".strip()
            message += "\n-Covid Resources India"
            
            for resource,recipient in join_data:
                if recipient.receive_notifications_all_cities or resource.city_id == city_id:
                    new_message = twilio_client.messages.create(
                         body=message,
                         from_= creds["twilio_number"],
                         to=f'+91{recipient.contact}'
                     )
            return "Success",200
        except:
            return "Error",500
        
    return render_template("contribute.html",state_names = state_names,blood_groups=blood_groups,services_indices = services_indices)   


@app.route('/admin/add-data', methods=['GET',"POST"])
def admin_add_data():
    if request.method == 'GET':
        if not session.get('logged_in'):
            return redirect("/admin/login")          
        else:        
            user = db_session.query(User).filter_by(username=session["username"]).first()
            if user.number_verified:
                return render_template("contribute.html",state_names = state_names,blood_groups=blood_groups,services_indices=services_indices)  
            else:
                return redirect("/admin/verify")
    elif request.method == "POST":
        data = request.get_json()["data"]
        state_id = int(data["states-select"]) 
        city_id = int(data["city-select"])
        name = data["donor-name"].strip()
        contact = data["donor-contact"].strip()
        resource_type = int(data["service"])
        address = data["resource-address"].strip().capitalize()
        additional_information = data["resource-info"].strip().capitalize()
                
        if data.get("resource-count"):
            resource_count = int(data['resource-count'])
        else:
            resource_count = ""

        if data.get("verification-check"):
            verified = int(data["verification-check"])
        else:
            verified = 0

        if data.get("blood-group"):
            blood_group = data["blood-group"]
        else:
            blood_group = ""

        if data.get("update-verification-check"):
            if int(data["update-verification-check"]) == 1:
                last_updated = datetime.now(timezone('Asia/Kolkata'))
            elif int(data["update-verification-check"]) == 0:
                if data.get("last-updated"):
                    date_str = data["last-updated"]
                    last_updated = datetime.strptime(date_str,date_format).astimezone(timezone('Asia/Kolkata'))
                else:
                    last_updated = ""
        else:
            last_updated = ""

        try:
            resource = {
                "resource_type":resource_type,
                "available":1,
                'verified':verified,
                "state_id":state_id,
                "city_id":city_id,
                'resource_count':resource_count,
                "is_approved_by_admin":1,
                "donor_or_recipient":0,
                "additional_information":additional_information,
                'last_updated' : last_updated}
            
            new_resource = Resources(**resource)
            db_session.add(new_resource)
            db_session.commit()
            
            donor = {"name":name,"contact":contact,"blood_group":blood_group,"resource_id":new_resource.id,"address":address}

            new_donor = Donors(**donor)
            db_session.add(new_donor)
            db_session.commit()
            return "Success",200
        except:
            return "Error",500

@app.route('/admin/manage-resource/<resource_id>', methods=['GET',"POST"])
def admin_manage_resource(resource_id):
    if request.method == 'GET':
        if not session.get('logged_in'):
            return redirect("/admin/login") 
        else:
            user = db_session.query(User).filter_by(username=session["username"]).first()
            if user.number_verified:
                resource = db_session.query(Resources).filter_by(id=resource_id).first()

                try:
                    name = resource.available_donors[0].name
                    contact = resource.available_donors[0].contact
                except:
                    name = resource.resource_recipients[0].name
                    contact =  resource.resource_recipients[0].contact
                
                state_id = resource.state_id
                city_id = resource.city_id

                location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]


                responses = {
                            "resource_name":services_indices[resource.resource_type].replace("-"," ").title(),
                            "name":name,
                            'contact':contact,
                            "available":resource.available,
                            "count":resource.resource_count,
                            "location":location,
                            "verified":resource.verified,
                            "additional_information":resource.additional_information if resource.additional_information else "",
                            "is_approved_by_admin":resource.is_approved_by_admin,
                            "resource_id":resource.id}

                try:
                    if resource.available_donors != []:
                        responses["address"] = resource.available_donors[0].address
                        if int(resource.resource_type) == 2:
                            responses["blood_group"] = resource.available_donors[0].blood_group
                            responses["blood_group_index"] = blood_groups.index(resource.available_donors[0].blood_group)
                    else:
                        responses["blood_group"] = ""
                        responses["blood_group_index"] = ""
                except:
                    if resource.resource_recipients != []:
                        responses["blood_group"] = resource.resource_recipients[0].blood_group
                        if int(resource.resource_type) == 2:
                            responses["address"] = resource.resource_recipients[0].address
                            responses["blood_group_index"] = blood_groups.index(resource_recipients.available_donors[0].blood_group)
                if resource.last_updated:
                    responses["last_updated"] = resource.last_updated.strftime(date_format)
                    
                return render_template("update_resource.html",responses = responses,blood_groups = blood_groups)  
            else:
                return redirect("/admin/verify")
            
    elif request.method == "POST":
        
        data = request.get_json()["data"]
        
        name = data["donor-name"]
        contact = data["donor-contact"]
        resource_count = int(data['resource-count']) if data.get('resource-count') else ""
        available = int(data["available-check"])
        admin_approved = int(data["admin-verification-check"])
        verified = int(data["verification-check"]) if data.get("verification-check") else 0
        blood_group = data["blood-group"] if data.get("blood-group") else ""
        last_updated = datetime.strptime(data["last-updated"],date_format).astimezone(timezone('Asia/Kolkata')) if data.get("last-updated") else ""
        address = data["resource-address"].capitalize()
        additional_information = data["resource-info"].capitalize()

        try:
            current_res = db_session.query(Resources).filter_by(id=resource_id).first()
            new_resource = db_session.query(Resources).filter_by(id=resource_id)
            
            resource_data = {"available":available,
                'verified':verified,
                'resource_count':resource_count,
                "additional_information":additional_information,
                "is_approved_by_admin":admin_approved,
                "donor_or_recipient":current_res.donor_or_recipient,
                "last_updated":last_updated}
            
            new_resource.update(resource_data)
            db_session.commit()
            
            if current_res.available_donors != []:
                person = {"name":name,"contact":contact,"blood_group":blood_group,"address":address}
                new_person = db_session.query(Donors).filter_by(id=current_res.available_donors[0].id)
                new_person.update(person)
                db_session.commit()
            else:
                person = {"name":name,"contact":contact,"blood_group":blood_group,"address":address}
                new_person = db_session.query(Recipients).filter_by(id=current_res.resource_recipients[0].id)
                new_person.update(person)
                db_session.commit()

            return "Success",200
        except:
            return "Error",500


@app.route('/manage-resource/<resource_id>', methods=['GET',"POST"])
def manage_resource(resource_id):
    if request.method == 'GET':
        resource = db_session.query(Resources).filter_by(id=resource_id).first()

        try:
            name = resource.available_donors[0].name
            contact = resource.available_donors[0].contact
        except:
            name = resource.resource_recipients[0].name
            contact =  resource.resource_recipients[0].contact
        
        state_id = resource.state_id
        city_id = resource.city_id

        location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]

        responses = {
                    "resource_name":services_indices[resource.resource_type].replace("-"," ").title(),
                    "name":name,
                    'contact':contact,
                    "available":resource.available,
                    "count":resource.resource_count,
                    "location":location,
                    "verified":resource.verified,
                    "additional_information":resource.additional_information if resource.additional_information else "",
                    "is_approved_by_admin":resource.is_approved_by_admin,
                    "resource_id":resource.id}
        
        try:
            if resource.available_donors != []:
                responses["address"] = resource.available_donors[0].address
                if int(resource.resource_type) == 2:
                    responses["blood_group"] = resource.available_donors[0].blood_group
                    responses["blood_group_index"] = blood_groups.index(resource.available_donors[0].blood_group)
            else:
                responses["blood_group"] = ""
                responses["blood_group_index"] = ""
        except:
            if resource.resource_recipients != []:
                responses["blood_group"] = resource.resource_recipients[0].blood_group
                if int(resource.resource_type) == 2:
                    responses["address"] = resource.resource_recipients[0].address
                    responses["blood_group_index"] = blood_groups.index(resource_recipients.available_donors[0].blood_group)
            else:
                responses["blood_group"] = ""
                responses["blood_group_index"] = ""
    
        if resource.last_updated:
            responses["last_updated"] = resource.last_updated.strftime(date_format)
                
        return render_template("update_resource.html",responses = responses,blood_groups = blood_groups)  

    elif request.method == "POST":
        data = request.get_json()["data"]
        
        name = data["donor-name"]
        contact = data["donor-contact"]
        resource_count = int(data['resource-count']) if data.get('resource-count') else ""
        available = int(data["available-check"])
        address = data["resource-address"].capitalize()
        additional_information = data["resource-info"].capitalize()
        
        if data.get("verification-check"):
            verified = int(data["verification-check"])
        else:
            verified = 0

        if data.get("blood-group"):
            blood_group = data["blood-group"]
        else:
            blood_group = ""

        last_updated = datetime.strptime(data["last-updated"],date_format).astimezone(timezone('Asia/Kolkata')) if data.get("last-updated") else ""

        try:
            current_res = db_session.query(Resources).filter_by(id=resource_id).first()
            new_resource = db_session.query(Resources).filter_by(id=resource_id)
            
            resource_data = {"available":available,
                'verified':verified,
                'resource_count':resource_count,
                "donor_or_recipient":current_res.donor_or_recipient,
                "last_updated":last_updated,
                "additional_information":additional_information
                }
            
            new_resource.update(resource_data)
            db_session.commit()
            
            if current_res.available_donors != []:
                person = {"name":name,"contact":contact,"blood_group":blood_group,"address":address}
                new_person = db_session.query(Donors).filter_by(id=current_res.available_donors[0].id)
                new_person.update(person)
                db_session.commit()
            else:
                person = {"name":name,"contact":contact,"blood_group":blood_group,"address":address}
                new_person = db_session.query(Recipients).filter_by(id=current_res.resource_recipients[0].id)
                new_person.update(person)
                db_session.commit()

            return "Success",200
        except:
            return "Error",500

@app.route('/inappropriate-resource/<resource_id>', methods=['GET',"POST"])
def mark_inappropriate(resource_id):
    if request.method == 'GET':
        resource = db_session.query(Resources).filter_by(id=resource_id).first()

        try:
            name = resource.available_donors[0].name
            contact = resource.available_donors[0].contact
        except:
            name = resource.resource_recipients[0].name
            contact =  resource.resource_recipients[0].contact
        
        state_id = resource.state_id
        city_id = resource.city_id

        location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]

        responses = {
                    "resource_name":services_indices[resource.resource_type].replace("-"," ").title(),
                    "name":name,
                    'contact':contact,
                    "available":resource.available,
                    "count":resource.resource_count,
                    "location":location,
                    "verified":resource.verified,
                    "additional_information":resource.additional_information if resource.additional_information else "",
                    "is_approved_by_admin":resource.is_approved_by_admin,
                    "resource_id":resource.id}
        
        try:
            if resource.available_donors != []:
                responses["address"] = resource.available_donors[0].address
                if int(resource.resource_type) == 2:
                    responses["blood_group"] = resource.available_donors[0].blood_group
                    responses["blood_group_index"] = blood_groups.index(resource.available_donors[0].blood_group)
            else:
                responses["blood_group"] = ""
                responses["blood_group_index"] = ""
        except:
            if resource.resource_recipients != []:
                responses["blood_group"] = resource.resource_recipients[0].blood_group
                if int(resource.resource_type) == 2:
                    responses["address"] = resource.resource_recipients[0].address
                    responses["blood_group_index"] = blood_groups.index(resource_recipients.available_donors[0].blood_group)
            else:
                responses["blood_group"] = ""
                responses["blood_group_index"] = ""
    
        if resource.last_updated:
            responses["last_updated"] = resource.last_updated.strftime(date_format)
                
        return render_template("mark_inappropriate.html",responses = responses,blood_groups = blood_groups)  

    elif request.method == "POST":
        data = request.get_json()["data"]
        try:
            inappropriate = db_session.query(InAppropriateResources).filter_by(resource_id=resource_id).first()
            if inappropriate is None:
                response = {
                "resource_id":resource_id,
                "comment":data["resource-info"]
                }

                resource = InAppropriateResources(**response)
                db_session.add(resource)
                db_session.commit()
                return "1",200
            else:
                return "2",200
        except:
            return "Error",500


@app.route('/admin/view-resources/<state_id>/<city_id>/<resource_type>', methods=['GET',"POST"])
def admin_view_resources(state_id,city_id,resource_type):
    if request.method == 'GET':
        if not session.get('logged_in'):
            return redirect("/admin/login")          
        else:       
            user = db_session.query(User).filter_by(username=session["username"]).first()
            if user.number_verified:
                state_id = int(state_id) 
                city_id = int(city_id)
                resource_type = int(resource_type)
                state_name = states_data[int(state_id) - 1]["name"]
                responses = {}
                response = []
                req_res_name = services_indices[resource_type]
                
                for resource in db_session.query(Resources).filter_by(state_id = state_id,
                                                                    city_id = city_id,
                                                                    resource_type=resource_type,
                                                                    donor_or_recipient=0).all():
                    for donor in resource.available_donors:
                        contact = donor.contact.replace(",","\n")
                        city_id = resource.city_id
                        location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]
                        address = f"\n\nAddress: {donor.address.strip()}" if donor.address and donor.address != "" else ""
                        additional_information = f"\n\nAdditional Information: {resource.additional_information}" if resource.additional_information and resource.additional_information != "" else ""
                        
                        resp_dict = {"name":donor.name + address + additional_information,
                                            'contact':contact,
                                            'location':location,
                                            "available":"Yes" if resource.available else "No",
                                            "donor_or_recipient":"Recipient" if resource.donor_or_recipient else "Donor",
                                            "count":resource.resource_count,
                                            "verified":"Yes" if resource.verified else "No",
                                            "is_approved_by_admin":"Yes" if resource.is_approved_by_admin else "No",
                                            "resource_id":resource.id}

                        if int(resource_type) == 2:
                            resp_dict["blood_group"] = donor.blood_group
                        response.append(resp_dict)
            
                responses[req_res_name] = response
                return render_template("view_resource.html",state_name = state_name,responses=responses)  
            else:
                return redirect("/admin/verify")

@app.route('/admin/view-inappropriate-resources', methods=['GET',"POST"])
def admin_view_inappropriate_resources():
    if request.method == 'GET':
        if not session.get('logged_in'):
            return redirect("/admin/login")          
        else:       
            user = db_session.query(User).filter_by(username=session["username"]).first()
            if user.number_verified:
                responses = {services_indices[ix]:[] for ix,res_name in enumerate(services_indices)}
                
                for resource,inappropriate_resource in db_session.query(Resources, InAppropriateResources).filter(InAppropriateResources.resource_id == Resources.id).all():
                    donor = resource.available_donors[0]
                    contact = donor.contact.replace(",","\n")
                    state_id = resource.state_id
                    state_name = states_data[int(state_id) - 1]["name"]
                    city_id = resource.city_id
                    location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]
                    
                    resp_dict = {"name":donor.name,
                                'location':location,
                                "comment":inappropriate_resource.comment,
                                "resource_id":resource.id}
                    
                    req_res_name = services_indices[resource.resource_type]
                    responses[req_res_name].append(resp_dict)
                
                if all(responses[key] == [] for key in responses.keys()):
                    responses = {}
                return render_template("view_inappropriate_resources.html",responses=responses)  
            else:
                return redirect("/admin/verify")
    
@app.route('/admin/login', methods=['GET',"POST"])
def admin_login():
    if request.method == 'GET':
        if not session.get('logged_in'):
            return render_template("admin_login.html")
        else:
            return redirect("/admin/home")
    else:
        name = request.form['username']
        passw = request.form['password']
        try:
            data = db_session.query(User).filter_by(username=name, password=passw).first()
            if data is not None:
                session['logged_in'] = True
                session['username'] = name
                return redirect("/admin/home")
            else:
                return render_template("admin_login.html",message="No such user exists.")
        except:
            return render_template("admin_login.html",message="There was an error")

@app.route('/admin/home', methods=['GET'])
def admin_home():
    if not session.get('logged_in'):
        return redirect("/admin/login")
    else:
        user = db_session.query(User).filter_by(username=session["username"]).first()
        if user.number_verified:
            return render_template('admin_home.html',state_names=state_names,services_indices=services_indices)
        else:
            return redirect("/admin/verify")

@app.route('/admin/register', methods=['GET',"POST"])
def admin_reg():
    if request.method == "GET":
        if not session.get('logged_in'):
            return render_template("admin_register.html")
        else:
            user = db_session.query(User).filter_by(username=session["username"]).first()
            if user.number_verified:
                return redirect("/admin/home")
            else:
                return redirect("/admin/verify")
    else:
        try:
            name = request.form['username']
            passw = request.form['password']
            data = db_session.query(User).filter_by(username=name).first()
            if data is None:
                new_user = User(
                    username=request.form['username'],
                    password=request.form['password'])
                db_session.add(new_user)
                db_session.commit()
                session['logged_in'] = True
                session['username'] = name
                return redirect("/admin/home")
            else:
                return render_template('admin_register.html',message="User already exists")
        except:
            return render_template('admin_register.html',message="There was an error")


@app.route('/admin/send-otp', methods=["POST"])
def admin_send_otp():
    otp = random.randint(1000,9999)
    number = request.form['recipient_contact']
    try:
        new_number = {
                "otp":otp,
                "username":session["username"]
            }
        
        registration = db_session.query(UserRegistrations).filter_by(username=session["username"]).first()
        
        if registration is None:
            new_number = UserRegistrations(**new_number)
            db_session.add(new_number)
            db_session.commit()

            message = twilio_client.messages \
                    .create(
                        body=f"Your covid-resources verification code is {otp}",
                        from_= creds["twilio_number"],
                        to=f'+91{number}'
                    )

            return "2",200
        else:
            contact = db_session.query(UserRegistrations).filter_by(username=session["username"])
            contact.update(new_number)
            db_session.commit()

            verification = {
                            "contact":number,
                            "number_verified":0
                        }

            user = db_session.query(User).filter_by(username=session["username"])
            user.update(verification)
            db_session.commit()

            message = twilio_client.messages \
                .create(
                        body=f"Your covid-resources verification code is {otp}",
                        from_= creds["twilio_number"],
                        to=f'+91{number}'
                    )
            return "2",200
    except:
        return "Error",500

@app.route('/admin/verify', methods=['GET',"POST"])
def admin_verify():
    if request.method == "GET":
        if not session.get('logged_in'):
            return redirect("/admin/login")
        else:
            user = db_session.query(User).filter_by(username=session["username"]).first()
            if user.number_verified:
                return redirect("/admin/home")
            else:
                return render_template("admin_verify.html")
    else:
        number = request.form['recipient_contact']
        otp = request.form['otp']
        try:
            resource = db_session.query(UserRegistrations).filter_by(username=session["username"]).first()
            if resource is not None:
                if resource.otp == int(otp):
                    verification = {
                        "contact":number,
                        "number_verified":1
                    }
                    user = db_session.query(User).filter_by(contact=number)
                    user.update(verification)
                    db_session.commit()
                    return "1",200
                else:
                    return "0",200
            else:
                return "Error",500  
        except:
            return "Error",500

@app.route('/register-recipient', methods=['GET',"POST"])
def register_recipient():
    if request.method == "POST":
        data = request.get_json()["data"]
        state_id = int(data["states-select"]) 
        city_id = int(data["city-select"])
        name = data['recipient-name'].strip()
        contact = data["recipient-contact"].strip()
        resource_type = int(data["service"])
        address = data["resource-address"].strip().capitalize()
        additional_information = data["resource-info"].strip().capitalize()
        resource_count = int(data["resource-count"]) if data.get("resource-count") else ""
        # receive_notifications = int(data["verification-check"]) if data.get("verification-check") else 0
        receive_notifications = 1
        other_cities = int(data["other-cities"]) if data.get("other-cities") else 0
        if data.get("blood-group"):
            blood_group = data["blood-group"]
        else:
            blood_group = ""
        
        last_updated = datetime.now(timezone('Asia/Kolkata'))
                
        try:
            resource = {
                "resource_type":resource_type,
                "available":1,
                'verified':1,
                "state_id":state_id,
                "city_id":city_id,
                'resource_count':resource_count,
                "is_approved_by_admin":1,
                "donor_or_recipient":1,
                "additional_information":additional_information,
                'last_updated' : last_updated}
            
            new_resource = Resources(**resource)
            db_session.add(new_resource)
            db_session.commit()
            
            recipient = {"name":name,"contact":contact,"blood_group":blood_group,"resource_id":new_resource.id,"address":address,"receive_notifications":receive_notifications,"receive_notifications_all_cities":other_cities}

            new_recipient = Recipients(**recipient)
            db_session.add(new_recipient)
            db_session.commit()

            new_number = {
                "contact":contact,
                "number_verified":1
            }

            registration = db_session.query(Registrations).filter_by(contact=contact)
            registration.update(new_number)
            db_session.commit()
            return "Success",200
        except:
            return "Error",500
    return render_template("register_recipient.html",state_names = state_names,services_indices=services_indices,blood_groups = blood_groups)   

@app.route('/unsubscribe-recipient', methods=['GET',"POST"])
def unsubscribe_recipient():
    if request.method == "POST":
        data = request.get_json()["data"]
        contact = data["recipient-contact"]
        try:
            new_number = {
                    "contact":contact,
                    "receive_notifications":0
                }

            recipient = db_session.query(Recipients).filter_by(contact=contact)
            recipient.update(new_number)
            db_session.commit()
            return "Success",200
        except:
            return "Error",500
    return render_template("unsubscribe_recipient.html")   


@app.route('/send-otp', methods=["POST"])
def send_otp():
    otp = random.randint(1000,9999)
    number = request.form['recipient_contact']
    method = request.form['method']
    try:
        registration = db_session.query(Registrations).filter_by(contact=number).first()
        if registration is None:
            if method == "subscribe":
                new_number = {
                "otp":otp,
                "contact":number,
                "number_verified":0
                }
                new_number = Registrations(**new_number)
                db_session.add(new_number)
                db_session.commit()

                message = twilio_client.messages \
                        .create(
                            body=f"Your covid-resources verification code is {otp}",
                            from_= creds["twilio_number"],
                            to=f'+91{number}'
                        )

                return "2",200
            else:
                return "1",200
        else:
            if registration.number_verified and method == "subscribe":
                return "1",200
            else:
                if method == "subscribe":
                    new_number = {
                        "otp":otp,
                        "contact":number,
                        "number_verified":0
                    }
                else:
                    new_number = {
                        "otp":otp,
                        "contact":number
                    }
                contact = db_session.query(Registrations).filter_by(contact=number)
                contact.update(new_number)
                db_session.commit()

                message = twilio_client.messages \
                    .create(
                         body=f"Your covid-resources verification code is {otp}",
                         from_= creds["twilio_number"],
                         to=f'+91{number}'
                     )
                return "2",200
    except:
        return "Error",500

@app.route('/verify-otp', methods=["POST"])
def verify_otp():
    number = request.form['recipient_contact']
    otp = request.form['otp']
    try:
        resource = db_session.query(Registrations).filter_by(contact=number).first()
        if resource is not None:
            if resource.otp == int(otp):
                return "1",200
            else:
                return "0",200
        else:
            return "Error",500  
    except:
        return "Error",500

@app.route("/admin/logout")
def logout():
    session['logged_in'] = False
    return redirect("/admin/login")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.secret_key = "123"
    app.run(host='0.0.0.0', port=port,debug=True)