from create_blog_form import CreatePostForm
from datetime import datetime
from flask import Flask, render_template, redirect, request, url_for
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
import os
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URI"]
# app.config["CKEDITOR_PKG_TYPE"] = "full-all"
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)

ckeditor = CKEditor(app)
Bootstrap(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    posts = db.relationship("Blog", backref="author")

    def get_id(self):
        return self.id

    def __repr__(self) -> str:
        return "<User %r>" % self.email


class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # Defing a foreign key
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    # Define one-to-many relationship
    comments = db.relationship("Comment", backref="blog")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    blog_id = db.Column(db.Integer, db.ForeignKey("blog.id"), nullable=False)
    # Relationship


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route("/")
def home():
    post_list = (
        current_user.posts if current_user.is_authenticated else Blog.query.all()
    )

    return render_template("index.html", posts=post_list)


@app.route("/posts/<id>")
def post(id):
    requested_post = Blog.query.get(id)
    comments = requested_post.comments
    users = []
    if comments:
        for comment in comments:
            user = User.query.get(comment.user_id)
            users.append(user)

    if requested_post:
        return render_template(
            "post.html",
            post=requested_post,
            is_author=requested_post.author == current_user,
            comment_texts=comments,
            users=users,
        )
    else:
        return "<h1>404 - No post found</h1>"


@app.route("/new_post", methods=["GET", "POST"])
@login_required
def create_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        blog_post = Blog(
            title=form.title.data,
            subtitle=form.subtitle.data,
            date=datetime.now().strftime("%b %d, %Y"),
            body=form.body.data,
            author_id=current_user.id,
            img_url=form.img_url.data,
        )
        db.session.add(blog_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("add_post.html", form=form)


@app.route("/post/<id>/add_comment", methods=["GET", "POST"])
@login_required
def add_comment(id):
    if request.method == "POST":
        data = request.form
        print(f"Comment({data['comment']},{current_user.id},{id})")
        comment = Comment(
            text=data["comment"],
            user_id=current_user.id,
            blog_id=id,
        )
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for("post", id=id))


@app.route("/edit_post/<id>", methods=["GET", "POST"])
@login_required
def edit_post(id):
    post = Blog.query.get(id)
    form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        author=post.author,
        img_url=post.img_url,
        body=post.body,
    )
    if form.validate_on_submit():
        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.date = datetime.now().strftime("%b %d, %Y")
        post.body = form.body.data
        post.author = form.author.data
        post.img_url = form.img_url.data
        db.session.commit()
        return redirect(url_for("post", id=post.id))
    return render_template("add_post.html", form=form)


@app.route("/delete/<id>")
@login_required
def delete_post(id):
    associated_comments = Comment.query.filter_by(blog_id=id).all()
    if associated_comments:
        for comment in associated_comments:
            db.session.delete(comment)
            db.session.commit()
    blog_post = Blog.query.get(id)
    if blog_post:
        db.session.delete(blog_post)
        db.session.commit()
    return redirect(url_for("home"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        email = data["email"]
        password = data["password"]

        user = User.query.filter_by(email=email).first()

        if not user:
            return render_template("login.html", error="No user found")

        if check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid email or password used")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.form
        password = generate_password_hash(data["password"])
        new_user = User(
            name=data["name"],
            email=data["email"],
            password=password,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


@app.context_processor
def inject_enumerate():
    return dict(enumerate=enumerate)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", debug=True)
