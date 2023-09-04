import datetime
import os
import re

import pymongo
from flask import Flask, render_template, session, request, redirect
from bson import ObjectId

from Mail import send_email

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = APP_ROOT + "/static"


myClient = pymongo.MongoClient('mongodb://localhost:27017/')
mydb = myClient["HotelManagement"]
admin_col = mydb["Admin"]
customer_col = mydb["Customer"]
emp_col = mydb["Employee"]
room_col = mydb["Rooms"]
room_type_col = mydb["RoomTypes"]
booking_col = mydb["Bookings"]
payment_col = mydb["Payment"]
house_keeping_room_col = mydb["HouseKeepingRoom"]
coins_col = mydb["Coins"]
customer_coins_col = mydb["CustomerCoins"]


app = Flask(__name__)
app.secret_key = "gfdhjffdgfgh"

if admin_col.count_documents({}) == 0:
    query = {"email": "admin@gmail.com", "password":"admin"}
    admin_col.insert_one(query)


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/aLogin")
def aLogin():
    return render_template("aLogin.html")


@app.route("/eLogin")
def eLogin():
    return render_template("eLogin.html")



@app.route("/cLogin")
def cLogin():
    return render_template("cLogin.html")


@app.route("/customerRegistration")
def customerRegistration():
    return render_template("customerRegistration.html")


@app.route("/customerReg1",methods=['post'])
def customerReg1():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    idProof = request.files.get("idProof")
    path = APP_ROOT + "/customerProof/" + idProof.filename
    idProof.save(path)
    customer_count = customer_col.count_documents({"$or":[{"email":email},{"phone":phone}]})
    if customer_count > 0:
        return render_template("message.html",msg='Duplicate Customer Details',color='text-danger')
    else:
        customer_col.insert_one({"name":name, "email":email, "phone":phone,"password":password,"idProof":idProof.filename,"points":0 })
        return render_template("message.html", msg='Customer Registered Successfully', color='text-success')


@app.route("/aLogin1",methods=['post'])
def aLogin1():
    email = request.form.get("email")
    password = request.form.get("password")
    admin_count = admin_col.count_documents({"email":email,"password":password})
    if admin_count > 0:
        session['role'] = 'admin'
        return render_template("admin.html")
    else:
        return render_template("message.html",msg='Invalid Login Details',color='text-danger')


@app.route("/admin")
def admin():
    return render_template("admin.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/addEmployee")
def addEmployee():
    return render_template("addEmployee.html")


@app.route("/addEmployee1",methods=['post'])
def addEmployee1():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    employee_type = request.form.get("employee_type")
    employee_count = emp_col.count_documents({"$or":[{"email":email},{"phone":phone}]})
    if employee_count > 0:
        return render_template("message.html",msg='Duplicate Employee Details',color='text-danger')
    else:
        emp_col.insert_one({"name":name, "email":email, "phone":phone,"password":password,"employee_type":employee_type})
        return render_template("message.html", msg='Employee Added', color='text-success')



@app.route("/viewEmployees")
def viewEmployees():
    employees = emp_col.find()
    employees = list(employees)
    if len(employees) == 0:
        return render_template("message.html",msg='Employees Not Found')
    return render_template("viewEmployees.html",employees=employees)


@app.route("/addRoom")
def addRoom():
    room_types = room_type_col.find()
    return render_template("addRoom.html",room_types=room_types)

@app.route("/addRooms1",methods=['post'])
def addRooms1():
    room_number = request.form.get("room_number")
    room_name = request.form.get("room_name")
    price_per_day = request.form.get("price_per_day")
    picture = request.files.get("picture")
    path = APP_ROOT + "/Room/" + picture.filename
    picture.save(path)
    room_type_id = request.form.get("room_type_id")
    query = {"$or":[{"room_name": room_name}, {"room_number":room_number}]}
    room_count = room_col.count_documents(query)
    if room_count > 0:
        return render_template("message.html", msg='Duplicate Room Details', color='text-danger')
    else:
        room_col.insert_one(
            {"room_name": room_name,"room_number" :room_number,"price_per_day": price_per_day, "picture": picture.filename,"status":'Available',"room_type_id":ObjectId(room_type_id)})
        return render_template("message.html", msg='Room Added', color='text-success')


@app.route("/viewRooms")
def viewRooms():
    query = {}
    room_type_id = request.args.get("room_type_id")
    check_in = request.args.get("check_in")
    check_out = request.args.get("check_out")
    print(room_type_id)
    if session['role'] == 'admin':
        query = {}
    elif session['role'] == 'employee':
        if room_type_id == 'all' or room_type_id == None:
            query = {}
        else:
            query = {"room_type_id": ObjectId(room_type_id), "status": 'Available'}
    rooms = room_col.find(query)
    room_types = room_type_col.find()
    rooms = list(rooms)
    if len(rooms) == 0:
        return render_template("message.html", msg='Rooms Not Available', color='text-warning')
    rooms2 = []
    if check_in == None:
        check_in = str(datetime.datetime.now().date())
    if check_out == None:
        check_out = str(datetime.datetime.now().date() + datetime.timedelta(days=1))
    if check_out != None and check_out != None:
        new_check_in_temp = datetime.datetime.strptime(check_in + " 15:00", "%Y-%m-%d %H:%M")
        new_check_out_temp = datetime.datetime.strptime(check_out + " 11:00", "%Y-%m-%d %H:%M")
        for room in rooms:
            is_room_available = True
            bookings = booking_col.find({"$or": [{"room_id": ObjectId(room['_id']), "status": 'Booked'},
                                                 {"room_id": ObjectId(room['_id']), "status": 'Checked In'}]})
            for booking in bookings:
                old_start_time = datetime.datetime.strptime(booking['check_in'] + " 15:00", "%Y-%m-%d %H:%M")
                old_end_time = datetime.datetime.strptime(booking['check_out'] + " 11:00", "%Y-%m-%d %H:%M")
                if ((new_check_in_temp >= old_start_time and new_check_in_temp <= old_end_time) and (
                        new_check_out_temp >= old_start_time and new_check_out_temp >= old_end_time)):
                    is_room_available = False

                elif ((new_check_in_temp <= old_start_time and new_check_in_temp <= old_end_time) and (
                        new_check_out_temp >= old_start_time and new_check_out_temp <= old_end_time)):
                    is_room_available = False

                elif ((new_check_in_temp >= old_start_time and new_check_in_temp >= old_end_time) and (
                        new_check_out_temp <= old_start_time and new_check_out_temp <= old_end_time)):
                    is_room_available = False

                elif ((new_check_in_temp >= old_start_time and new_check_in_temp <= old_end_time) and (
                        new_check_out_temp >= old_start_time and new_check_out_temp <= old_end_time)):
                    is_room_available = False
            if is_room_available:
                rooms2.append(room)
        else:
          rooms2 = rooms

    elif session['role'] == 'customer':
        if room_type_id == 'all' or room_type_id == None:
             query = {}
        else:
            query = {"room_type_id": ObjectId(room_type_id),"status":'Available'}
    rooms = room_col.find(query)
    room_types = room_type_col.find()
    rooms  = list(rooms)
    if len(rooms) == 0:
        return render_template("message.html",msg='Rooms Not Available',color='text-warning')
    rooms2 = []
    if session['role'] == 'customer':
        if check_in == None:
            check_in = str(datetime.datetime.now().date())
        if check_out == None:
            check_out = str(datetime.datetime.now().date()+ datetime.timedelta(days=1))
    if check_out!=None and check_out!=None:
        new_check_in_temp = datetime.datetime.strptime(check_in + " 15:00", "%Y-%m-%d %H:%M")
        new_check_out_temp = datetime.datetime.strptime(check_out + " 11:00", "%Y-%m-%d %H:%M")
        for room in rooms:
            is_room_available = True
            bookings = booking_col.find({"$or": [{"room_id": ObjectId(room['_id']), "status": 'Booked'},
                                                 {"room_id": ObjectId(room['_id']), "status": 'Checked In'}]})
            for booking in bookings:
                old_start_time = datetime.datetime.strptime(booking['check_in'] + " 15:00", "%Y-%m-%d %H:%M")
                old_end_time = datetime.datetime.strptime(booking['check_out'] + " 11:00", "%Y-%m-%d %H:%M")
                if ((new_check_in_temp >= old_start_time and new_check_in_temp <= old_end_time) and (
                        new_check_out_temp >= old_start_time and new_check_out_temp >= old_end_time)):
                    is_room_available = False

                elif ((new_check_in_temp <= old_start_time and new_check_in_temp <= old_end_time) and (
                        new_check_out_temp >= old_start_time and new_check_out_temp <= old_end_time)):
                    is_room_available = False

                elif ((new_check_in_temp >= old_start_time and new_check_in_temp >= old_end_time) and (
                        new_check_out_temp <= old_start_time and new_check_out_temp <= old_end_time)):
                    is_room_available = False

                elif ((new_check_in_temp >= old_start_time and new_check_in_temp <= old_end_time) and (
                        new_check_out_temp >= old_start_time and new_check_out_temp <= old_end_time)):
                    is_room_available = False
            if is_room_available:
                rooms2.append(room)
    else:
        rooms2 = rooms

    return render_template("viewRooms.html", rooms=rooms2, check_in=check_in, check_out=check_out, room_types=room_types, get_room_type_by_id=get_room_type_by_id,room_type_id=room_type_id,str=str)


def get_room_type_by_id(room_type_id):
    room_type = room_type_col.find_one({"_id":ObjectId(room_type_id)})
    return room_type

@app.route("/add_room_type")
def add_room_type():
    return render_template("add_room_type.html")


@app.route("/add_room_type1",methods=['post'])
def add_room_type1():
    room_type = request.form.get("room_type")
    room_type_count = room_type_col.count_documents({"room_type":room_type})
    if room_type_count > 0:
        return render_template("message.html",msg='Room Type Exists "'+room_type+'"',color='text-danger')
    else:
        room_type_col.insert_one({"room_type":room_type})
        return render_template("message.html", msg='Room Type Added "' + room_type + '"', color='text-success')


@app.route("/view_room_types",methods=['post'])
def view_room_types():
    room_id = request.form.get("room_id")
    room_types = room_type_col.find({"room_id":ObjectId(room_id)})
    return render_template("view_room_types.html",room_types=room_types)


@app.route("/eLogin1", methods=['post'])
def eLogin1():
    email = request.form.get("email")
    password = request.form.get("password")
    query = {"email": email, "password": password}
    count = emp_col.count_documents(query)
    if count > 0:
        results = emp_col.find(query)
        for result in results:
            session['employee_id'] = str(result['_id'])
            session['role'] = 'employee'
            return render_template("employee.html")

    else:
        return render_template("message.html", msg='Invalid Login Details', color='text-danger')


@app.route("/employee")
def employee():
    return render_template("employee.html")



@app.route("/cLogin1", methods=['post'])
def cLogin1():
    email = request.form.get("email")
    password = request.form.get("password")
    query = {"email": email, "password": password}
    count = customer_col.count_documents(query)
    if count > 0:
        results = customer_col.find(query)
        for result in results:
            session['customer_id'] = str(result['_id'])
            session['role'] = 'customer'
            return redirect("/customer")

    else:
        return render_template("message.html", msg='Invalid Login Details', color='text-danger')


@app.route('/customer')
def customer():
    customer = customer_col.find_one({"_id":ObjectId(session['customer_id'])})
    customer_points = customer_col.find_one({"_id":ObjectId(session['customer_id'])})
    points = customer_points['points']
    coins = coins_col.find()
    coins2 = []
    for coin in coins:
        if int(points) >= int(coin['points']):
            coins2.append(coin)
    return render_template("customer.html",customer=customer,coins2=coins2)


@app.route("/bookRoom",methods=['post'])
def bookRoom():
    room_id = request.form.get("room_id")
    return render_template("bookRoom.html",room_id=room_id)



@app.route("/bookRoom1",methods=['post'])
def bookRoom1():
    room_id = request.form.get("room_id")
    room = room_col.find_one({"_id":ObjectId(room_id)})
    price_per_day = room['price_per_day']
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    check_in2= check_in
    check_out2= check_out
    check_in = datetime.datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out = datetime.datetime.strptime(check_out, "%Y-%m-%d").date()
    print(check_in,check_out)
    days_difference = check_out - check_in
    no_of_days = days_difference.days
    print(no_of_days)
    totalAmount = int(no_of_days) * int(price_per_day)

    new_check_in_temp = datetime.datetime.strptime(check_in2+" 15:00", "%Y-%m-%d %H:%M")
    new_check_out_temp = datetime.datetime.strptime(check_out2+" 11:00", "%Y-%m-%d %H:%M")
    bookings = booking_col.find({"$or" : [{"room_id": ObjectId(room_id),"status": 'Booked'},{"room_id": ObjectId(room_id),"status": 'Checked In'}]})

    for booking in bookings:
        old_start_time = datetime.datetime.strptime(booking['check_in'] +" 15:00", "%Y-%m-%d %H:%M")
        old_end_time = datetime.datetime.strptime(booking['check_out'] +" 11:00", "%Y-%m-%d %H:%M")
        if ((new_check_in_temp >= old_start_time and new_check_in_temp <= old_end_time) and (
                new_check_out_temp >= old_start_time and new_check_out_temp >= old_end_time)):
            return render_template("message.html", msg='Room Not Available in these Dates', color='text-danger')

        elif ((new_check_in_temp <= old_start_time and new_check_in_temp <= old_end_time) and (
                new_check_out_temp >= old_start_time and new_check_out_temp <= old_end_time)):
            return render_template("message.html", msg='Room Not Available in these Dates', color='text-danger')

        elif ((new_check_in_temp >= old_start_time and new_check_in_temp >= old_end_time) and (
                new_check_out_temp <= old_start_time and new_check_out_temp <= old_end_time)):
            return render_template("message.html", msg='Room Not Available in these Dates', color='text-danger')

        elif ((new_check_in_temp >= old_start_time and new_check_in_temp <= old_end_time) and (
                new_check_out_temp >= old_start_time and new_check_out_temp <= old_end_time)):
            return render_template("message.html", msg='Room Not Available in these Dates', color='text-danger')

    return render_template("bookRoom1.html",totalAmount=totalAmount,room=room,no_of_days=no_of_days,room_id=room_id,check_in=check_in,check_out=check_out)



@app.route("/bookRoom2",methods=['post'])
def bookRoom2():
    room_id = request.form.get("room_id")
    totalAmount = request.form.get("totalAmount")
    totalAmount2=totalAmount
    no_of_days = request.form.get("no_of_days")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    customer_id = session['customer_id']
    customer_coins = customer_coins_col.find({"customer_id":ObjectId(customer_id)})
    customer_coins2 = []
    for customer_coin in customer_coins:
        if int(customer_coin['days']) > 0:
            customer_coins2.append(customer_coin)
    if len(customer_coins2) == 0:
        return render_template("payAmount.html",totalAmount2=totalAmount2, room_id=room_id, totalAmount=totalAmount, no_of_days=no_of_days,check_in=check_in, check_out=check_out,int=int)
    else:
        return render_template("choose_coins.html",customer_coins2=customer_coins2,get_coin_by_customerCoinId=get_coin_by_customerCoinId,room_id=room_id, totalAmount=totalAmount, no_of_days=no_of_days,check_in=check_in, check_out=check_out)



@app.route("/choose_coins1",methods=['post'])
def choose_coins1():
    customer_coin_id = request.form.get("customer_coin_id")
    room_id = request.form.get("room_id")
    totalAmount = request.form.get("totalAmount")
    totalAmount2 =totalAmount
    no_of_days = request.form.get("no_of_days")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    room = room_col.find_one({"_id": ObjectId(room_id)})
    customer_coin = customer_coins_col.find_one({"_id": ObjectId(customer_coin_id)})
    coin = coins_col.find_one({"_id":customer_coin['coin_id']})
    if int(no_of_days) <= int(customer_coin['days']):
        totalAmount = int(totalAmount) - (int(totalAmount) * int(coin['discount_price']))/100
        discount_days = no_of_days
    else:
        discount_days = int(customer_coin['days'])
        remaining_days = int(no_of_days) - int(discount_days)
        discount_days_amount = int(room['price_per_day']) * int(discount_days)
        discount_days_amount = (discount_days_amount) - (discount_days_amount * int(coin['discount_price']))/100
        remaining_days_amount = (int(room['price_per_day']))* remaining_days
        print(discount_days_amount)
        print(remaining_days_amount)
        totalAmount = discount_days_amount + remaining_days_amount

    return render_template("payAmount.html",discount_days=discount_days,customer_coin_id=customer_coin_id, room_id=room_id, totalAmount=totalAmount, totalAmount2=totalAmount2, no_of_days=no_of_days,check_in=check_in, check_out=check_out,int=int)



def get_coin_by_customerCoinId(coin_id):
    coin = coins_col.find_one({'_id':ObjectId(coin_id)})
    return coin


@app.route("/payAmount",methods=['post'])
def payAmount():
    room_id = request.form.get("room_id")
    totalAmount = request.form.get("totalAmount")
    no_of_days = request.form.get("no_of_days")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    result = booking_col.insert_one({"no_of_days":no_of_days,"totalAmount":totalAmount,"check_in":check_in,"check_out":check_out,"room_id":ObjectId(room_id),"customer_id":ObjectId(session['customer_id']),"status":'Booked'})
    booking_id = result.inserted_id
    payment_col.insert_one({"booking_id":ObjectId(booking_id),"totalAmount":totalAmount,"date":datetime.datetime.now()})
    query = {"$set":{"status":'Locked'}}
    room_col.update_one({"_id":ObjectId(room_id)},query)

    customer_coin_id = request.form.get("customer_coin_id")
    discount_days = request.form.get("discount_days")
    if customer_coin_id !=None:
        customer_coin = customer_coins_col.find_one({"_id": ObjectId(customer_coin_id)})
        query = {"$set": {"days": int(customer_coin['days']) - int(discount_days)}}
        customer_coins_col.update_one({"_id": ObjectId(customer_coin_id)}, query)
    return render_template("message.html",msg='Room Booked Successfully',color='text-success')


@app.route("/viewCustomerBookings")
def viewCustomerBookings():
    query = {}
    if session['role'] == 'admin':
        room_id = request.args.get("room_id")
        query = {"room_id":ObjectId(room_id)}
    elif session['role'] == 'customer':
        query = {'customer_id':ObjectId(session['customer_id'])}
    elif session['role'] == 'employee':
        room_id = request.args.get("room_id")
        if room_id != None:
           query = {"room_id":ObjectId(room_id)}
        else:
            query = {}
    bookings = booking_col.find(query)
    return render_template("viewCustomerBookings.html",get_employee_by_bookings=get_employee_by_bookings,get_customer_by_bookings=get_customer_by_bookings,bookings=bookings,get_room_id_by_booking=get_room_id_by_booking)

def get_customer_by_bookings(customer_id):
    customer = customer_col.find_one({"_id":ObjectId(customer_id)})
    return customer

def get_employee_by_bookings(employee_id):
    employee = emp_col.find_one({"_id":ObjectId(employee_id)})
    return employee

def get_room_id_by_booking(room_id):
    room = room_col.find_one({"_id":ObjectId(room_id)})
    return room


@app.route("/cancelBooking",methods=['post'])
def cancelBooking():
    booking_id = request.form.get("booking_id")
    booking = booking_col.find_one({'_id':ObjectId(booking_id)})
    room_id = booking['room_id']
    query = {"$set":{"status":'Booking Cancelled'}}
    booking_col.update_one({"_id":ObjectId(booking_id)},query)
    query2 = {"$set":{"status":'Available'}}
    room_col.update_one({"_id":ObjectId(room_id)},query2)
    return redirect("/viewCustomerBookings")


@app.route("/bookRoom_for_customer",methods=['post'])
def bookRoom_for_customer():
    room_id = ObjectId(request.form.get("room_id"))
    totalAmount = request.form.get("totalAmount")
    no_of_days = request.form.get("no_of_days")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    return render_template("bookRoom_for_customer.html",room_id=room_id,totalAmount=totalAmount,no_of_days=no_of_days,check_in=check_in,check_out=check_out)


@app.route("/bookRoom_for_customer1",methods=['post'])
def bookRoom_for_customer1():
    room_id = ObjectId(request.form.get("room_id"))
    print(room_id)
    room = room_col.find_one({"_id":ObjectId(room_id)})
    totalAmount = request.form.get("totalAmount")
    no_of_days = request.form.get("no_of_days")
    check_in = request.form.get("check_in")
    check_out = request.form.get("check_out")
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    idProof = request.files.get("idProof")
    path = APP_ROOT + "/customerProof/" + idProof.filename
    idProof.save(path)
    customer_count = customer_col.count_documents({"email": email})
    if customer_count > 0:
        customer = customer_col.find_one({"email": email})
        customer_id = customer['_id']
    else:
        result = customer_col.insert_one({"name":name,"email":email,"phone":phone,"password":"1234","idProof":idProof.filename,"points":0})
        customer_id = result.inserted_id
    result = booking_col.insert_one({"no_of_days": no_of_days, "totalAmount": totalAmount, "check_in": check_in, "check_out": check_out,"room_id": ObjectId(room_id), "customer_id": ObjectId(customer_id),"employee_id":ObjectId(session['employee_id']), "status": 'Booked'})
    booking_id = result.inserted_id
    payment_col.insert_one({"booking_id": ObjectId(booking_id), "totalAmount": totalAmount, "date": datetime.datetime.now()})
    query = {"$set": {"status": 'Locked'}}
    room_col.update_one({"_id": ObjectId(room_id)}, query)
    customer = customer_col.find_one({"_id":ObjectId(customer_id)})
    email = customer['email']
    password = customer['password']
    send_email("Hotel Management", "Your  Room Booked Successfully \n Room ('"+room['room_name']+"') \n Use this below Account Credentials To  Login Access Account \n Email : "+email+" \n Password :"+password+"", email)
    return render_template("message.html",msg='Room Booked Successfully',color='text-success')


@app.route("/check_IN",methods=['post'])
def check_IN():
    booking_id = request.form.get("booking_id")
    query = {"$set":{"status":'Checked In'}}
    booking_col.update_one({"_id":ObjectId(booking_id)},query)
    return render_template("message.html",msg='The Booked Room is Checked IN',color='text-primary')


@app.route("/check_out",methods=['post'])
def check_out():
    booking_id = request.form.get("booking_id")
    booking = booking_col.find_one({"_id":ObjectId(booking_id)})
    room_id = booking['room_id']
    customer_id = booking['customer_id']
    customer = customer_col.find_one({"_id":ObjectId(customer_id)})
    points = customer['points']

    no_of_days = request.form.get("no_of_days")
    points = no_of_days
    points = int(customer['points']) + int(points)
    print(points)
    query2 = {"$set":{"points":points}}
    customer_col.update_one({"_id":ObjectId(customer_id)},query2)

    query = {"$set":{"status":'Room Checked out'}}
    booking_col.update_one({"_id":ObjectId(booking_id)},query)

    query3 = {"$set":{"status":'Available'}}
    room_col.update_one({"_id":ObjectId(room_id)},query3)
    return render_template("message.html",msg='The Booked Room is Checked Out',color='text-primary')


@app.route("/editCustomer")
def editCustomer():
    customer_id = request.args.get("customer_id")
    customer = customer_col.find_one({"_id":ObjectId(customer_id)})
    return render_template("editCustomer.html",customer=customer,customer_id=customer_id)


@app.route("/editCustomer1",methods=['post'])
def editCustomer1():
    customer_id = request.form.get("customer_id")
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    query = {"$set":{'name':name,"email":email,"phone":phone,"password":password}}
    customer_col.update_one({"_id":ObjectId(customer_id)},query)
    return redirect("/customer")


@app.route("/addHouseKeeping",methods=['post'])
def addHouseKeeping():
    room_id = request.form.get("room_id")
    return render_template("addHouseKeeping.html",room_id=room_id)


@app.route("/addHouseKeeping1",methods=['post'])
def addHouseKeeping1():
    room_id = request.form.get("room_id")
    work = request.form.get("work")
    house_keeping_room_col.insert_one({"work":work,"room_id":ObjectId(room_id),"status":'completed',"employee_id":ObjectId(session['employee_id']),"date":datetime.datetime.now()})
    return redirect("/viewRooms")


@app.route("/viewHouseKeeping",methods=['post'])
def viewHouseKeeping():
    room_id = request.form.get("room_id")
    house_keepings = house_keeping_room_col.find({"room_id":ObjectId(room_id),"employee_id":ObjectId(session['employee_id'])})
    return render_template("viewHouseKeeping.html",house_keepings=house_keepings,get_employee_by_house_keeping=get_employee_by_house_keeping)


def get_employee_by_house_keeping(employee_id):
    employee = emp_col.find_one({"_id":ObjectId(employee_id)})
    return employee

@app.route("/addCoins")
def addCoins():
    return render_template("addCoins.html")

@app.route("/addCoins1",methods=['post'])
def addCoins1():
    coin_name = request.form.get("coin_name")
    days = request.form.get("days")
    points = request.form.get("points")
    discount_price = request.form.get("discount_price")
    coins_col.insert_one({"coin_name":coin_name,"days":days,"points":points,"discount_price":discount_price})
    return render_template("message.html",msg='Coins Added Successfully',color='text-success')

@app.route("/viewCoins")
def viewCoins():
    coins = coins_col.find()
    coins = list(coins)
    if len(coins) ==0:
        return render_template("message.html",msg='Coins Not Found')
    return render_template("viewCoins.html",coins=coins)


@app.route("/Claim_coin")
def Claim_coin():
    coin_id = request.args.get("coin_id")
    days = request.args.get("days")
    customer_points = request.args.get("customer_points")
    points = request.args.get("points")
    customer_id = session['customer_id']
    coin = coins_col.find_one({"_id":ObjectId(coin_id)})
    coin_count = customer_coins_col.count_documents({"coin_id":ObjectId(coin_id),"customer_id":ObjectId(customer_id)})
    if coin_count == 0:
        customer_coins_col.insert_one({"coin_id":ObjectId(coin_id),"days":days,"customer_id":ObjectId(customer_id)})
        customer_points = int(customer_points) - int(points)
        query = {"$set":{"points":customer_points}}
        customer_col.update_one({"_id":ObjectId(customer_id)},query)
        return render_template("message.html", msg='Coin Claimed', color='text-primary')
    else:
        customer_coin = customer_coins_col.find_one({"coin_id":ObjectId(coin_id),"customer_id":ObjectId(customer_id)})
        days = int(customer_coin['days']) + int(days)
        query = {"$set":{"days":days}}
        customer_coins_col.update_one({"coin_id":ObjectId(coin_id),"customer_id":ObjectId(customer_id)},query)
        customer_points = int(customer_points) - int(points)
        query1 = {"$set": {"points": customer_points}}
        customer_col.update_one({"_id": ObjectId(customer_id)}, query1)
        return render_template("message.html", msg='Coin Claimed', color='text-primary')




@app.route("/viewClaims")
def viewClaims():
    customer_id = request.args.get("customer_id")
    customer_coins = customer_coins_col.find({"customer_id":ObjectId(customer_id)})
    customer_coins = list(customer_coins)
    if len(customer_coins) ==0:
        return render_template("message.html",mgs='No Claims',color='text-warning')
    return render_template("viewClaims.html",customer_coins=customer_coins,get_coin_by_customer_coin=get_coin_by_customer_coin)

def get_coin_by_customer_coin(coin_id):
    coin = coins_col.find_one({"_id":ObjectId(coin_id)})
    return coin


@app.route("/viewPayments",methods=['post'])
def viewPayments():
    booking_id = request.form.get("booking_id")
    payment = payment_col.find_one({"booking_id":ObjectId(booking_id)})
    return render_template("viewPayments.html",payment=payment)


app.run(debug=True)

