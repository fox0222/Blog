from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
# from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from hashlib import md5
import os

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ["FLASK_KEY"]
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DB_URI']
db = SQLAlchemy(model_class=Base)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_post"
    id = db.Column(Integer, primary_key=True)
    title = db.Column(String(250), unique=True, nullable=False)
    subtitle = db.Column(String(250), nullable=False)
    date = db.Column(String(250), nullable=False)
    body = db.Column(Text, nullable=False)
    img_url = db.Column(String(250), nullable=False)
    author_id = db.Column(Integer, ForeignKey("users.id"))
    comments = db.relationship("Comment", backref="post")



class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(Integer, primary_key=True)
    email = db.Column(String(100), unique=True, nullable=False)
    password = db.Column(String(250), nullable=False)
    name = db.Column(String(100), nullable=False)
    posts = db.relationship("BlogPost", backref="author")
    comments = db.relationship("Comment", backref="author")

    def avatar(self):
        email_hash = md5(self.email.lower().encode("utf-8")).hexdigest()
        avatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=identicon"
        return avatar_url

    def __repr__(self):
        return f"<User: {self.name}>"


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(Integer, primary_key=True)
    text = db.Column(Text, nullable=False)
    author_id = db.Column(Integer, ForeignKey("users.id"))
    post_id = db.Column(Integer, ForeignKey("blog_post.id"))


@login_manager.user_loader
def user_loader(user_id):
    return db.session.get(User, int(user_id))





# TODO: Create a User table for all your registered users. 


# with app.app_context():
#     db.create_all()

def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return func(*args, **kwargs)
        else:
            abort(403)
    return wrapper


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        users = User.query.all()
        emails = [user.email for user in users]
        if form.email.data not in emails:
            user = User(email=form.email.data,
                        password=generate_password_hash(form.password.data, method="scrypt", salt_length=8),
                        name=form.name.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("get_all_posts"))
        else:
            flash("You've already signed up with that email. Log in instead!")
            return redirect(url_for("login"))
    return render_template("register.html", form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    users = User.query.all()
    emails = [user.email for user in users]
    if form.validate_on_submit():
        if form.email.data in emails:
            user = User.query.filter_by(email=form.email.data).first()
            if check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Password incorrect, try again.")
                return redirect(url_for("login"))
        else:
            flash("This email does not exist. Try again.")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    comments = Comment.query.all()
    users = User.query.all()
    avatars_dict = {user.id: user.avatar() for user in users}
    if form.validate_on_submit():
        if current_user.is_authenticated:
            author = current_user.id
            comment = Comment(text=form.comment.data,
                              author_id=author,
                              post_id=post_id)
            db.session.add(comment)
            db.session.commit()
            return redirect(url_for("show_post", post_id=post_id))
        else:
            flash("You need to log in.")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post,
                           form=form, comments=comments,
                           avatars=avatars_dict)



# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    author = current_user.id
    if form.validate_on_submit():
        new_post = BlogPost(
            author_id=author,
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        author_id=current_user.id,
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/delete_comment/<int:comment_id>")
@admin_only
def delete_comment(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    db.session.delete(comment)
    db.session.commit()
    return redirect(url_for("show_post", post_id=comment.post_id))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=False, port=5002)
