from uuid import uuid4
from functools import wraps
import os
from flask import (
    Flask,
    render_template,
    url_for,
    redirect,
    session,
    request,
    flash,
)

from werkzeug.exceptions import NotFound
from todos.utils import (
    error_for_list_title,
    find_list_by_id,
    error_for_todo_item,
    find_todo_by_id,
    delete_todo_by_id,
    complete_all,
    delete_list_by_id,
    todos_remaining,
    is_list_completed,
    sort_items,
    is_todo_completed,
)

app = Flask(__name__)
app.secret_key='secret1'

def require_list(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        list_id = kwargs.get('list_id')
        lst = find_list_by_id(list_id, session['lists'])
        if not lst:
            raise NotFound(description="List not found")
        return f(lst=lst, *args, **kwargs)

    return decorated_function

def require_todo(f):
    @wraps(f)
    @require_list
    def decorated_function(lst, *args, **kwargs):
        todo_id = kwargs.get('todo_id')
        todo = find_todo_by_id(todo_id, lst)
        if not todo:
            raise NotFound(description="Todo not found")
        return f(lst=lst, todo=todo, *args, **kwargs)

    return decorated_function

@app.context_processor
def list_utilities_processor():
    return dict(is_list_completed=is_list_completed)

@app.before_request
def initialize_session():
    if 'lists' not in session:
        session['lists'] = []

@app.route("/")
def index():
    return redirect(url_for('get_lists'))

@app.route("/lists/new")
def add_todo():
    return render_template('new_list.html')

@app.route("/lists", methods=["GET"])
def get_lists():
    lists = sort_items(session['lists'], is_list_completed)
    return render_template('lists.html', lists=lists, todos_remaining=todos_remaining)

@app.route("/lists", methods=["POST"])
def create_list():
    title = request.form["list_title"].strip()
    error = error_for_list_title(title, session['lists'])
    if error:
        flash(error, "error")
        return render_template('new_list.html', title=title)
    
    session['lists'].append({'id': str(uuid4()), 'title': title, 'todos': []})
    flash("The list has been created.", "success")
    session.modified = True
    return redirect(url_for('get_lists'))

@app.route("/lists/<list_id>")
@require_list
def show_list(lst, list_id):
    
    #This code is duplicated in add_todo_item
    todos = sort_items(lst['todos'], is_todo_completed)
    return render_template('list.html', lst=lst, todos=todos)

@app.route("/lists/<list_id>/todos", methods=["POST"])
@require_list
def add_todo_item(lst, list_id):
    title = request.form['todo'].strip()
    error = error_for_todo_item(title)
    
    if error:
        flash(error, "error")
        #this is duplicated code
        todos = sort_items(lst['todos'], is_todo_completed)
        return render_template('list.html', title=title, lst=lst, todos=todos)
    lst['todos'].append({'id': str(uuid4()), 'title': title, 'completed': False})
    session.modified = True
    flash("The todo was added.", "success")
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<list_id>/todos/<todo_id>/toggle", methods=['Post'])
@require_todo
def toggle_todo_item(lst, todo, list_id, todo_id):
    
    todo['completed'] = not todo['completed']
    flash("The todo has been updated.", "success")
    session.modified = True
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<list_id>/todos/<todo_id>/delete", methods=['POST'])
@require_todo
def delete_todo_item(lst, todo, list_id, todo_id):
    
    delete_todo_by_id(todo_id, lst)
    session.modified = True
    flash("The todo has been deleted.", "success")
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<list_id>/complete_all", methods=['POST'])
@require_list
def complete_all_todos(lst, list_id):
    
    complete_all(lst)
    session.modified = True
    return redirect(url_for('show_list', list_id=list_id))

@app.route("/lists/<list_id>/edit", methods=['GET', 'POST'])
@require_list
def edit_list(lst, list_id):
    
    if request.method == 'POST':
        title = request.form['new_title'].strip()
        error = error_for_list_title(title, session['lists'])
        if error:
            flash(error, "error")
            return render_template('edit_list.html', lst=lst, invalid_title=title)
        lst['title'] = title
        session.modified = True
        flash(f"Title successfully changed to '{title}'")
        return redirect(url_for('show_list', list_id=list_id))
    return render_template('edit_list.html', lst=lst)

@app.route("/lists/<list_id>/delete", methods=['POST'])
@require_list
def delete_list(lst, list_id):

    title = lst['title']
    session['lists'] = delete_list_by_id(list_id, session['lists'])
    session.modified = True
    flash(f"'{title}' was successfully deleted")
    return redirect(url_for('get_lists'))

if __name__ == "__main__":
    if os.environ.get('FLASK_ENV') == 'production':
        app.run(debug=False)
    else:
        app.run(debug=True, port=8080)