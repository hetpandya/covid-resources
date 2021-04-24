import os
from flask import Flask,render_template,session,redirect
from flask import request,jsonify
import base64
import json
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
        resources_query = data["resources"]
        responses = {}
        services_indices = ["remdesivir","beds","plasma","oxygen","tiffins"]

        location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]
        
        for req_res in resources_query:
            response = []
            for resource in db_session.query(Resources).filter_by(state_id = state_id,
                                                                city_id = city_id,
                                                                resource_type=int(req_res),
                                                                donor_or_recipient=0,is_approved_by_admin=1).all():
                for donor in resource.available_donors:
                    contact = [contact+"<br>".replace(",","") for contact in donor.contact.split(",")]
                    resp_dict = {"name":donor.name,
                                "resource_id":resource.id,
                                'contact':contact,
                                'location':location,
                                "available":"Yes" if resource.available else "No",
                                "count":resource.resource_count,
                                "verified":"Yes" if resource.verified else "No"}

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
    state_names = [(ix+1,state["name"]) for ix,state in enumerate(states_data)]
    return render_template("index.html",state_names = state_names)  

@app.route('/add-data', methods=['GET',"POST"])
def add_data():
    blood_groups = "A+, A-, B+, B-, O+, O-, AB+, AB-".split(",")
    blood_groups = [group.strip() for group in blood_groups]
    state_names = [(ix+1,state["name"]) for ix,state in enumerate(states_data)]
    if request.method == "POST":
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

        try:
            resource = {
                "resource_type":resource_type,
                "available":1,
                'verified':verified,
                "state_id":state_id,
                "city_id":city_id,
                'resource_count':resource_count,
                "is_approved_by_admin":1,
                "donor_or_recipient":0}
            
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
        
    return render_template("contribute.html",state_names = state_names,blood_groups=blood_groups)   


@app.route('/admin/add-data', methods=['GET',"POST"])
def admin_add_data():
    if request.method == 'GET':
        if not session.get('logged_in'):
            return redirect("/admin/login")          
        else:        
            blood_groups = "A+, A-, B+, B-, O+, O-, AB+, AB-".split(",")
            blood_groups = [group.strip() for group in blood_groups]
            state_names = [(ix+1,state["name"]) for ix,state in enumerate(states_data)]
            return render_template("contribute.html",state_names = state_names,blood_groups=blood_groups)  
    elif request.method == "POST":
        data = request.get_json()["data"]
        
        state_id = int(data["states-select"]) 
        city_id = int(data["city-select"])
        name = data["donor-name"]
        contact = data["donor-contact"]
        resource_type = int(data["service"])
        resource_count = int(data['resource-count'])
        
        if data.get("verification-check"):
            verified = int(data["verification-check"])
        else:
            verified = 0

        if data.get("blood-group"):
            blood_group = data["blood-group"]
        else:
            blood_group = ""

        try:
            resource = {
                "resource_type":resource_type,
                "available":1,
                'verified':verified,
                "state_id":state_id,
                "city_id":city_id,
                'resource_count':resource_count,
                "is_approved_by_admin":1,
                "donor_or_recipient":0}
            
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
            blood_groups = "A+, A-, B+, B-, O+, O-, AB+, AB-".split(",")
            blood_groups = [group.strip() for group in blood_groups]  

            services_indices = ["remdesivir","beds","plasma","oxygen","tiffins"]

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
                        "resource_name":services_indices[resource.resource_type].title(),
                        "name":name,
                        'contact':contact,
                        "available":resource.available,
                        "count":resource.resource_count,
                        "location":location,
                        "verified":resource.verified,
                        "is_approved_by_admin":resource.is_approved_by_admin,
                        "resource_id":resource.id}

            if int(resource.resource_type) == 2:
                try:
                    responses["blood_group"] = resource.available_donors[0].blood_group
                    responses["blood_group_index"] = blood_groups.index(resource.available_donors[0].blood_group)
                except:
                    responses["blood_group"] = resource.resource_recipients[0].blood_group
                    responses["blood_group_index"] = blood_groups.index(resource_recipients.available_donors[0].blood_group)
                    
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

        try:
            current_res = db_session.query(Resources).filter_by(id=resource_id).first()
            new_resource = db_session.query(Resources).filter_by(id=resource_id)
            
            resource_data = {"available":available,
                'verified':verified,
                'resource_count':resource_count,
                "is_approved_by_admin":admin_approved,
                "donor_or_recipient":current_res.donor_or_recipient}
            
            new_resource.update(resource_data)
            db_session.commit()
            
            if current_res.available_donors != []:
                person = {"name":name,"contact":contact,"blood_group":blood_group}
                new_person = db_session.query(Donors).filter_by(id=current_res.available_donors[0].id)
                new_person.update(person)
                db_session.commit()
            else:
                person = {"name":name,"contact":contact,"blood_group":blood_group}
                new_person = db_session.query(Recipients).filter_by(id=current_res.resource_recipients[0].id)
                new_person.update(person)
                db_session.commit()

            return "Success",200
        except:
            return "Error",500


@app.route('/manage-resource/<resource_id>', methods=['GET',"POST"])
def manage_resource(resource_id):
    if request.method == 'GET':
        blood_groups = "A+, A-, B+, B-, O+, O-, AB+, AB-".split(",")
        blood_groups = [group.strip() for group in blood_groups]  

        services_indices = ["remdesivir","beds","plasma","oxygen","tiffins"]

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
                    "resource_name":services_indices[resource.resource_type].title(),
                    "name":name,
                    'contact':contact,
                    "available":resource.available,
                    "count":resource.resource_count,
                    "location":location,
                    "verified":resource.verified,
                    "is_approved_by_admin":resource.is_approved_by_admin,
                    "resource_id":resource.id}

        if int(resource.resource_type) == 2:
            try:
                responses["blood_group"] = resource.available_donors[0].blood_group
                responses["blood_group_index"] = blood_groups.index(resource.available_donors[0].blood_group)
            except:
                responses["blood_group"] = resource.resource_recipients[0].blood_group
                responses["blood_group_index"] = blood_groups.index(resource_recipients.available_donors[0].blood_group)
                
        return render_template("update_resource.html",responses = responses,blood_groups = blood_groups)  

    elif request.method == "POST":
        data = request.get_json()["data"]
        
        name = data["donor-name"]
        contact = data["donor-contact"]
        resource_count = int(data['resource-count'])
        available = int(data["available-check"])
        
        if data.get("verification-check"):
            verified = int(data["verification-check"])
        else:
            verified = 0

        if data.get("blood-group"):
            blood_group = data["blood-group"]
        else:
            blood_group = ""
        try:
            current_res = db_session.query(Resources).filter_by(id=resource_id).first()
            new_resource = db_session.query(Resources).filter_by(id=resource_id)
            
            resource_data = {"available":available,
                'verified':verified,
                'resource_count':resource_count,
                "donor_or_recipient":current_res.donor_or_recipient}
            
            new_resource.update(resource_data)
            db_session.commit()
            
            if current_res.available_donors != []:
                person = {"name":name,"contact":contact,"blood_group":blood_group}
                new_person = db_session.query(Donors).filter_by(id=current_res.available_donors[0].id)
                new_person.update(person)
                db_session.commit()
            else:
                person = {"name":name,"contact":contact,"blood_group":blood_group}
                new_person = db_session.query(Recipients).filter_by(id=current_res.resource_recipients[0].id)
                new_person.update(person)
                db_session.commit()

            return "Success",200
        except:
            return "Error",500


@app.route('/admin/view-resources/<state_id>', methods=['GET',"POST"])
def admin_view_resources(state_id):
    if request.method == 'GET':
        if not session.get('logged_in'):
            return redirect("/admin/login")          
        else:       
            state_id = int(state_id) 
            state_name = states_data[int(state_id) - 1]["name"]
            responses = {}
            services_indices = ["remdesivir","beds","plasma","oxygen","tiffins"]

            for req_res,req_res_name in enumerate(services_indices):
                response = []
                for resource in db_session.query(Resources).filter_by(state_id = state_id,
                                                                    resource_type=int(req_res),
                                                                    donor_or_recipient=0).all():
                    for donor in resource.available_donors:
                        contact = donor.contact.replace(",","\n")
                        city_id = resource.city_id
                        location = states_data[state_id - 1]["districts"][city_id - 1]["name"] + ", " + states_data[state_id - 1]["name"]

                        resp_dict = {"name":donor.name,
                                            'contact':contact,
                                            'location':location,
                                            "available":"Yes" if resource.available else "No",
                                            "donor_or_recipient":"Recipient" if resource.donor_or_recipient else "Donor",
                                            "count":resource.resource_count,
                                            "verified":"Yes" if resource.verified else "No",
                                            "is_approved_by_admin":"Yes" if resource.is_approved_by_admin else "No",
                                            "resource_id":resource.id}

                        if int(req_res) == 2:
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
        state_names = [(ix+1,state["name"]) for ix,state in enumerate(states_data)]
        return render_template('admin_home.html',state_names=state_names)

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