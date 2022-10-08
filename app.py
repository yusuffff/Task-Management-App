import datetime
import random

from flask import Flask, render_template, request,redirect,flash,session
from google.auth.transport import requests
from google.cloud import datastore
import google.oauth2.id_token

app = Flask(__name__)
app.secret_key = 'kiwi'
datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()


@app.route('/')
def root():
    return render_template('index.html')

@app.route('/login')
def login():
    if session.get('loggedin_email'):
        return redirect('/homepage')
    else:
        id_token = request.cookies.get("token")
        if id_token:
            try:
                claims = google.oauth2.id_token.verify_firebase_token(id_token,requests.Request())
                session['loggedin_email'] = claims['email']
                return redirect('/homepage')
            except ValueError as exc:
                 error_message = str(exc)
                 return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/homepage')
def homepage():
    user_info = None
    _data = list()
    if session.get('loggedin_email'):
        # GET USER RECORDS
        entity_key = datastore_client.key('user_records', session.get('loggedin_email'))
        user_info = datastore_client.get(entity_key)
        # If user does not exist in datastore, create record for user
        if not user_info:
            add_users(session.get('loggedin_email'),[])
            user_info = datastore_client.get(entity_key)
        # get boardid list
        board_list_of_ids = user_info['board_list']
        # get board details and append it in _data
        for board_id in board_list_of_ids:
            entity_key = datastore_client.key('taskboard', int(board_id))
            board_details = datastore_client.get(entity_key)
            _data.append(board_details)

    return render_template('homepage.html', data = _data, current_user = session.get('loggedin_email'))

# # Mark a task as completed
# @app.route('/markcompleted/<task_id>/<board_id>')
# def markcompleted(task_id,board_id):
#     # get user details
#     entity_key = datastore_client.key('task', int(task_id))
#     userinfo = datastore_client.get(entity_key)
#
#     entity_key = datastore_client.key('task', int(task_id))
#     entity = datastore.Entity(key = entity_key)
#     entity.update({
#         'title':userinfo['title'],
#         'assigned_user':userinfo['assigned_user'],
#         'due_date':userinfo['due_date'],
#         'date_completed': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
#         'marked_completed': True
#     })
#     datastore_client.put(entity)
#     return redirect('/board_details/'+board_id)




# ADD board
@app.route('/addboard', methods=['POST'])
def addboard():
    board_list_of_ids = list()
    tasklist=list()
    user_info = None
    if session.get('loggedin_email'):
        id = random.getrandbits(63)
        entity_key = datastore_client.key('taskboard', id)
        entity = datastore.Entity(key = entity_key)
        entity.update({
            'createdBy':session.get('loggedin_email'),
            'board_title':request.form ['title'],
            'board_users':[],
            'task_list':[],
            'task_name':[]
        })
        datastore_client.put(entity)

        # get user details
        entity_key = datastore_client.key('user_records', session.get('loggedin_email'))
        user_info = datastore_client.get(entity_key)

        board_list_of_ids  = user_info['board_list']
        if int(id) not in board_list_of_ids:
            board_list_of_ids.append(id)

            entity_key = datastore_client.key('user_records', session.get('loggedin_email'))
            entity = datastore.Entity(key = entity_key)

            entity.update({
            'user_email': session.get('loggedin_email'),
            'board_list': board_list_of_ids
            })

            datastore_client.put(entity)
    return redirect('/homepage')

# ADD task
@app.route('/addtask', methods=['POST'])
def addtask():
    task_list_of_ids = list()
    # user_info = None
    entity_key = datastore_client.key('taskboard', int(request.form['board_id']))
    board_info = datastore_client.get(entity_key)
    taskname  = board_info['task_name']
    if request.form['title'] not in taskname:
        taskname.append(request.form['title'])
        board_info.update({'task_name':taskname})
        datastore_client.put(board_info)
        if session.get('loggedin_email'):
            id = random.getrandbits(63)
            entity_key = datastore_client.key('task', id)
            entity = datastore.Entity(key = entity_key)
            entity.update({
                'title':request.form['title'],
                'assigned_user':request.form['assignedto'],
                'due_date':request.form['duedate'],
                'date_completed': None,
                'marked_completed': False,
                'task_id':id
            })
            datastore_client.put(entity)
            # get user details
            entity_key = datastore_client.key('taskboard', int(request.form['board_id']))
            entity=datastore_client.get(entity_key)
            board_list_of_taskids  = entity['task_list']
            board_list_of_taskids.append(id)
            entity.update({'task_list':board_list_of_taskids})
            datastore_client.put(entity)

    else:
        flash('Task name already exist')



    return redirect('/board_details/'+request.form['board_id'])


# Board detail
@app.route('/board_details/<board_id>')
def boarddetails(board_id):
    task_info = list()
    # get board details
    entity_key = datastore_client.key('taskboard', int(board_id))
    board_details = datastore_client.get(entity_key)

    task_ids = board_details['task_list']

    for task_id in task_ids:
        entity_key = datastore_client.key('task', int(task_id))
        task_details = datastore_client.get(entity_key)
        task_info.append(task_details)
    _data = {
        'board_members':board_details['board_users'],
        'task_details' : task_info,
        'board_id': board_id,
        'user_list': get_users(),
        'board_owner':board_details['createdBy'],
        'current_user': session.get('loggedin_email')
    }
    return render_template('/board_detail.html', data = _data, result = counter(board_id))

# Add member to board
@app.route('/addboardmember', methods=['POST'])
def addboardmember():
    board_id = request.form.get('board_id')

    entity_key = datastore_client.key('taskboard', int(board_id))
    board_details = datastore_client.get(entity_key)
    # get board users and append new user to it
    board_members = board_details['board_users']

    if request.form['email'] not in board_members:
        board_members.append(request.form.get('email'))
        # update board details for user
        entity_key = datastore_client.key('taskboard', int(board_id))
        entity = datastore.Entity(key = entity_key)
        entity.update({
            'board_title': board_details['board_title'],
            'board_users': board_members,
            'createdBy': board_details['createdBy'],
            'task_list':board_details['task_list'],
        })
        datastore_client.put(entity)

    # get user details and append board to it
    entity_key = datastore_client.key('user_records', request.form['email'])
    user_details = datastore_client.get(entity_key)
    board_list = user_details['board_list']
    if int(board_id) not in board_list:
        board_list.append(board_id)

        # update user details
        entity_key = datastore_client.key('user_records',  request.form['email'])
        entity = datastore.Entity(key = entity_key)
        entity.update({
            'board_list':board_list,
            'user_email': user_details['user_email'],
        })
        datastore_client.put(entity)

    return redirect('/board_details/'+board_id)

# Delete task
@app.route('/delete_task/<task_id>/<board_id>')
def delete_task(task_id,board_id):

    # get board details
    entity_key = datastore_client.key('taskboard', int(board_id))
    board_details = datastore_client.get(entity_key)
    task_ids = board_details['task_list']

    # update board kind
    task_ids.remove(int(task_id))
    # entity_key = datastore_client.key('taskboard', int(board_id))
    entity = datastore.Entity(key = entity_key)


    entity.update({
    'createdBy': board_details['createdBy'],
    'board_title': board_details['board_title'],
    'board_users': board_details['board_users'],
    'task_list':task_ids
    })
    datastore_client.put(entity)

    # delete from task kind
    entity_key_task = datastore_client.key('task', int(task_id))
    datastore_client.delete(entity_key_task)

    return redirect('/board_details/'+board_id)



# Save user details
def add_users(email, board_list):
    entity_key = datastore_client.key('user_records', email)
    entity = datastore.Entity(key = entity_key)
    entity.update({
    'user_email': email,
    'board_list': board_list
    })
    datastore_client.put(entity)

# user list
def get_users():
    query = datastore_client.query(kind = "user_records")
    results = query.fetch()
    data = list()
    for item in results:
        if item['user_email'] != session.get('loggedin_email'):
            data.append(item['user_email'])
    return data

#

# Mark a task as completed
@app.route('/markcompleted/<task_id>/<board_id>')
def markcompleted(task_id,board_id):
    # get user details
    entity_key = datastore_client.key('task', int(task_id))
    userinfo = datastore_client.get(entity_key)

    entity_key = datastore_client.key('task', int(task_id))
    entity = datastore.Entity(key = entity_key)
    entity.update({
        'title':userinfo['title'],
        'assigned_user':userinfo['assigned_user'],
        'due_date':userinfo['due_date'],
        'date_completed': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'marked_completed': True
    })
    datastore_client.put(entity)
    return redirect('/board_details/'+board_id)

@app.route('/edittask', methods=['POST'])
def edittask():
    name = request.form['title']
    due_date = request.form['duedate']
    assignedTo = request.form['assignedto']
    task_id = request.form['task_id']
    board_id = request.form['board_id']

    entity_key = datastore_client.key('task', int(task_id))

    details = datastore_client.get(entity_key)

    entity = datastore.Entity(key = entity_key)
    entity.update({
        'title':name,
        'assigned_user':assignedTo,
        'due_date':due_date,
        'date_completed': details['date_completed'],
        'marked_completed': details['marked_completed']
    })
    datastore_client.put(entity)
    return redirect('/board_details/'+board_id)

@app.route('/unassign_task/<task_id>/<board_id>')
def unassign_task(task_id, board_id):
    entity_key = datastore_client.key('task', int(task_id))

    details = datastore_client.get(entity_key)

    entity = datastore.Entity(key = entity_key)
    entity.update({
        'title':details['title'],
        'assigned_user':None,
        'due_date':details['due_date'],
        'date_completed': details['date_completed'],
        'marked_completed': details['marked_completed']
    })
    datastore_client.put(entity)
    return redirect('/board_details/'+board_id)

@app.route('/renameboard', methods=['POST'])
def renameboard():
    board_id = request.form['board_id']
    title = request.form['title']
    entity_key = datastore_client.key('taskboard', int(board_id))

    details = datastore_client.get(entity_key)

    entity = datastore.Entity(key = entity_key)

    entity.update({
        'createdBy':details['createdBy'],
        'board_title':title,
        'board_users':details['board_users'],
        'task_list':details['task_list']
    })
    datastore_client.put(entity)
    return redirect('/homepage')

def counter(board_id):
    active_task = 0
    completed_task = 0
    total_task = 0
    task_completed_now = 0
    id =  int(board_id)

    entity_key = datastore_client.key('taskboard', id)
    print('board_id', type (id))
    entity = datastore_client.get(entity_key)
    task_ids = entity['task_list']
    total_task = len(task_ids)
    for task_id in task_ids:
        entity_key = datastore_client.key('task', int(task_id))
        print('task_id', type (task_id))
        entity = datastore_client.get(entity_key)
        if entity['marked_completed']:
            if entity['date_completed'] >= datetime.datetime.now().strftime('%Y-%m-%d %H:%M'):
                task_completed_now = task_completed_now + 1
            completed_task = completed_task + 1
        else:
            _task = active_task + 1

    results = {
        'completed_task':completed_task,
        'total_task':total_task,
        'task_completed_now':task_completed_now,
        'active_task':active_task
    }

    return results


@app.route('/removeboardmember', methods=['POST'])
def removeUser():

    data = request.form
    board_id = data.get('board_id')
    user=data.get('email')
    list_of_task_users = list()
    list_of_board_ids =list()
    isUnassignedSucessful=[]

    # remove user from board table
    entity_key = datastore_client.key('taskboard', int(board_id))
    taskinfo = datastore_client.get(entity_key)
    list_of_task_users = taskinfo['board_users']
    list_of_task_users.remove(user)
    taskinfo.update({"board_users":list_of_task_users})
    datastore_client.put(taskinfo)

    # Remove board id from user table
    entity_key = datastore_client.key('user_records', user)
    entity= datastore_client.get(entity_key)
    list_of_board_ids = entity['board_list']
    list_of_board_ids.remove(board_id)


    entity.update({'board_list':list_of_board_ids})
    datastore_client.put(entity)

    # remove user from asigned records
    board_ids = taskinfo['task_list']
    address_list = []



    # get task details
    for item in board_ids:
        entity_key = datastore_client.key('task', int(item))
        data= datastore_client.get(entity_key)
        address_list.append(data)



    for item in address_list:
        if item['assigned_user'] == user :
            print(item)
            entity_key = datastore_client.key("task", int(item['task_id']))
            entity = datastore_client.get(entity_key)
            entity.update({'assigned_user':None})
            datastore_client.put(entity)


    return redirect('/board_details/'+ board_id)



if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
