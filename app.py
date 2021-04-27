import os
from flask import Flask,render_template,session,redirect
from flask import request,jsonify
import base64
import json
from datetime import datetime
from pytz import timezone
from models import *

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
                db_query = db_session.query(Resources).filter_by(state_id = state_id,
                                                                resource_type=int(req_res),
                                                                donor_or_recipient=0,
                                                                is_approved_by_admin=1).all()
            else:
                db_query = db_session.query(Resources).filter_by(state_id = state_id,
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
        name = data["donor-name"]
        contact = data["donor-contact"]
        resource_type = int(data["service"])
        address = data["resource-address"].capitalize()
        additional_information = data["resource-info"].capitalize()
        
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
            return render_template("contribute.html",state_names = state_names,blood_groups=blood_groups,services_indices=services_indices)  
    elif request.method == "POST":
        data = request.get_json()["data"]
        state_id = int(data["states-select"]) 
        city_id = int(data["city-select"])
        name = data["donor-name"]
        contact = data["donor-contact"]
        resource_type = int(data["service"])
                
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
                'last_updated' : last_updated}
            
            new_resource = Resources(**resource)
            db_session.add(new_resource)
            db_session.commit()
            
            donor = {"name":name,"contact":contact,"blood_group":blood_group,"resource_id":new_resource.id}

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


@app.route('/admin/view-resources/<state_id>/<city_id>/<resource_type>', methods=['GET',"POST"])
def admin_view_resources(state_id,city_id,resource_type):
    if request.method == 'GET':
        if not session.get('logged_in'):
            return redirect("/admin/login")          
        else:       
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
        return render_template('admin_home.html',state_names=state_names,services_indices=services_indices)

@app.route('/admin/register', methods=['GET',"POST"])
def admin_reg():
    if request.method == "GET":
        if not session.get('logged_in'):
            return render_template("admin_register.html")
        else:
            return redirect("/admin/home")
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
                return redirect("/admin/home")
            else:
                return render_template('admin_register.html',message="User already exists")
        except:
            return render_template('admin_register.html',message="There was an error")

@app.route("/admin/logout")
def logout():
    session['logged_in'] = False
    return redirect("/admin/login")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.secret_key = "123"
    app.run(host='0.0.0.0', port=port,debug=True)