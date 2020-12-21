#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from datetime import datetime
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask.globals import session
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from flask_migrate import Migrate, show
from sqlalchemy.orm import backref
from sqlalchemy.orm import joinedload
from sqlalchemy.sql.base import Executable
from sqlalchemy import select
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String(1000))
    website = db.Column(db.String(250))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))

    shows = db.relationship('Show', backref="venue", cascade="all, delete, delete-orphan", lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    shows = db.relationship('Show', backref="artist", cascade="all, delete, delete-orphan")


class Show(db.Model):
    __tablename__ = 'shows'
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey(
        'Venue.id'))
    venue_name = db.Column(db.String)
    artist_id = db.Column(db.Integer, db.ForeignKey(
        'Artist.id'))
    artist_name = db.Column(db.String)
    artist_image_link = db.Column(db.String(500))
    venue_image_link = db.Column(db.String(500))
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    # date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(value, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
def VenuesRoutes():
    @app.route('/venues')
    def venues():
        # TODO: replace with real venues data.
        #       num_shows should be aggregated based on number of upcoming shows per venue.
        data = [{
            "city": "San Francisco",
            "state": "CA",
            "venues": [{
                "id": 1,
                "name": "The Musical Hop",
                "num_upcoming_shows": 0,
            }, {
                "id": 3,
                "name": "Park Square Live Music & Coffee",
                "num_upcoming_shows": 1,
            }]
        }]

        areas = {}
        for venue in db.session.query(Venue.id, Venue.name, Venue.city, Venue.state, db.func.count(Show.id)).outerjoin(Venue.shows).filter(Show.start_time >= datetime.now()).group_by(Venue).all():
            venues = areas.get(venue[2], {"venues": []})["venues"]
            venues.append({
                'id': venue[0],
                "name": venue[1],
                "num_upcoming_shows": venue[4]
            })

            areas[venue.city] = {
                "city": venue[2],
                "state": venue[3],
                "venues": venues
            }

        return render_template('pages/venues.html', areas=areas.values())

    @app.route('/venues/search', methods=['POST'])
    def search_venues():
        # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
        # seach for Hop should return "The Musical Hop".
        # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
        response = {
            "count": 1,
            "data": [{
                "id": 2,
                "name": "The Dueling Pianos Bar",
                "num_upcoming_shows": 0,
            }]
        }

        data = db.session.query(Venue.id, Venue.name, db.func.count(Show.id)).outerjoin(
            Venue.shows).filter(Show.start_time >= datetime.now()).group_by(Venue.id).all()

        results = {
            "count": len(data),
            "data": list(map(lambda row: {"id": row[0], "name": row[1], "num_upcoming_shows": row[2]}, data))
        }
        return render_template('pages/search_venues.html', results=results, search_term=request.form.get('search_term', ''))

    @app.route('/venues/<int:venue_id>')
    def show_venue(venue_id):
        venue = Venue.query.get(venue_id)

        venue.past_shows = Show.query.filter_by(venue_id=venue.id).filter(
            Show.start_time < datetime.now()).all()
        venue.past_shows_count = len(venue.past_shows)

        venue.upcoming_shows = Show.query.filter_by(
            venue_id=venue.id).filter(Show.start_time >= datetime.now()).all()
        venue.upcoming_shows_count = len(venue.upcoming_shows)

        venue.genres = venue.genres.split(',')
        return render_template('pages/show_venue.html', venue=venue)

    # Create Venue
    #  ----------------------------------------------------------------

    @app.route('/venues/create', methods=['GET'])
    def create_venue_form():
        form = VenueForm()
        return render_template('forms/new_venue.html', form=form)

    @app.route('/venues/create', methods=['POST'])
    def create_venue_submission():
        try:
            newVenu = Venue(
                name=request.form.get('name'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                address=request.form.get('address'),
                phone=request.form.get('phone'),
                facebook_link=request.form.get('facebook_link'),
                image_link=request.form.get('image_link'),
                genres=','.join(request.form.getlist('genres')),
                website=request.form['website'],
                seeking_talent=True if request.form['seeking_talent'] == '1' else False,
                seeking_description=request.form['seeking_description'],
            )

            db.session.add(newVenu)
            db.session.commit()

            # on successful db insert, flash success
            flash('Venue ' + request.form['name'] +
                  ' was successfully listed!', 'success')

            return render_template('pages/home.html')
        except Exception as error:
            db.session.rollback()
            flash('An error occurred. Venue ' +
                  request.form['name'] + ' could not be listed because of the error: ' + error.__str__(), 'danger')
            return redirect(url_for('create_venue_form'))
        finally:
            db.session.close()

    @app.route('/venues/<venue_id>/delete', methods=['GET'])
    def delete_venue(venue_id):
        try:
            db.session.delete(Venue.query.get(venue_id))
            db.session.commit()
            flash('venue has been deleted', 'success')
        except Exception as error:
            db.session.rollback()
            flash('an error occured: ' + error.__str__(), 'danger')
        finally:
            db.session.close()
        return redirect(url_for('index'))

    #  Update venues
    #  ----------------------------------------------------------------

    @app.route('/venues/<int:venue_id>/edit', methods=['GET'])
    def edit_venue(venue_id):
        venue = Venue.query.get(venue_id)
        venue.genres = venue.genres.split(',')
        form = VenueForm(obj=venue)

        return render_template('forms/edit_venue.html', form=form, venue=venue)

    @app.route('/venues/<int:venue_id>/edit', methods=['POST'])
    def edit_venue_submission(venue_id):
        try:
            venue = Venue.query.get(venue_id)
            venue.name = request.form.get('name')
            venue.city = request.form.get('city')
            venue.state = request.form.get('state')
            venue.address = request.form.get('address')
            venue.phone = request.form.get('phone')
            venue.facebook_link = request.form.get('facebook_link')
            venue.image_link = request.form.get('image_link')
            venue.genres = ','.join(request.form.getlist('genres'))
            venue.website = request.form['website']
            venue.seeking_talent = True if request.form['seeking_talent'] == '1' else False
            venue.seeking_description = request.form['seeking_description']

            db.session.execute('update shows set venue_name=\'' +
                               venue.name + '\', venue_image_link=\'' + venue.image_link + '\' where venue_id=' + str(venue.id))

            flash('Venue has been updated successfully', 'success')

            db.session.commit()
            return redirect(url_for('show_venue', venue_id=venue_id))
        except Exception as error:
            flash('An error occured: ' + error.__str__(), 'danger')
            db.session.rollback()
            return redirect(url_for('edit_venue', venue_id=venue_id))
        finally:
            db.session.close()


VenuesRoutes()

#  Artists
#  ----------------------------------------------------------------


def ArtistRoutes():
    @app.route('/artists')
    def artists():
        return render_template('pages/artists.html', artists=Artist.query.all())

    @app.route('/artists/search', methods=['POST'])
    def search_artists():
        found = Artist.query.filter(Artist.name.like(
            '%' + request.form.get('search_term', '') + '%')).all()
        response = {
            "count": len(found),
            "data": found
        }
        return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

    @app.route('/artists/<int:artist_id>')
    def show_artist(artist_id):
        # shows the venue page with the given venue_id
        # TODO: replace with real venue data from the venues table, using venue_id
        data1 = {
            "past_shows": [{
                "venue_id": 1,
                "venue_name": "The Musical Hop",
                "venue_image_link": "https://images.unsplash.com/photo-1543900694-133f37abaaa5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=400&q=60",
                "start_time": "2019-05-21T21:30:00.000Z"
            }],
            "upcoming_shows": [],
            "past_shows_count": 1,
            "upcoming_shows_count": 0,
        }

        artist = Artist.query.get(artist_id)
        artist.past_shows = Show.query.filter_by(artist_id=artist.id).filter(
            Show.start_time < datetime.now()).all()
        artist.past_shows_count = len(artist.past_shows)

        artist.upcoming_shows = Show.query.filter_by(
            artist_id=artist.id).filter(Show.start_time >= datetime.now()).all()
        artist.upcoming_shows_count = len(artist.upcoming_shows)

        artist.genres = artist.genres.split(',')
        return render_template('pages/show_artist.html', artist=artist)

    #  Update Artist
    #  ----------------------------------------------------------------

    @app.route('/artists/<int:artist_id>/edit', methods=['GET'])
    def edit_artist(artist_id):
        artist = Artist.query.get(artist_id)
        artist.genres = artist.genres.split(',')
        form = ArtistForm(obj=artist)
        return render_template('forms/edit_artist.html', form=form, artist=artist)

    @app.route('/artists/<int:artist_id>/edit', methods=['POST'])
    def edit_artist_submission(artist_id):
        try:
            artist = Artist.query.get(artist_id)
            artist.name = request.form['name']
            artist.city = request.form['city']
            artist.state = request.form['state']
            artist.phone = request.form['phone']
            artist.facebook_link = request.form['facebook_link']
            artist.genres = ','.join(request.form.getlist('genres'))
            artist.image_link = request.form['image_link']

            db.session.execute('update shows set artist_name=\'' + artist.name +
                               '\', artist_image_link=\'' + artist.image_link + '\' where artist_id=' + str(artist.id))
            db.session.commit()

            flash('artist updated successfully', 'success')

            return redirect(url_for('show_artist', artist_id=artist_id))
        except Exception as error:

            db.session.rollback()

            flash('An error occured: ' + error.__str__(), 'danger')

            return redirect(url_for('edit_artist', artist_id=artist_id))
        finally:
            db.session.close()

    #  Create Artist
    #  ----------------------------------------------------------------

    @app.route('/artists/create', methods=['GET'])
    def create_artist_form():
        form = ArtistForm()
        return render_template('forms/new_artist.html', form=form)

    @app.route('/artists/create', methods=['POST'])
    def create_artist_submission():
        try:
            db.session.add(Artist(
                name=request.form['name'],
                city=request.form['city'],
                state=request.form['state'],
                phone=request.form['phone'],
                genres=','.join(request.form.getlist('genres')),
                facebook_link=request.form['facebook_link'],
                image_link=request.form['image_link']
            ))
            db.session.commit()
            flash('Artist ' + request.form['name'] +
                  ' was successfully listed!', 'success')

            return render_template('pages/home.html')
        except Exception as error:
            db.session.rollback()
            flash('An error occures: ' + error.__str__(), 'danger')

            return redirect(url_for('create_artist_form'))
        finally:
            db.session.close()

    @app.route('/artists/<artist_id>/delete', methods=['GET'])
    def delete_artist(artist_id):
        try:
            db.session.delete(Artist.query.get(artist_id))
            db.session.commit()
            flash('Artist has been deleted', 'success')
        except Exception as error:
            db.session.rollback()
            flash('an error occured: ' + error.__str__(), 'danger')
        finally:
            db.session.close()
        return redirect(url_for('index'))


ArtistRoutes()

#  Shows
#  ----------------------------------------------------------------


def ShowsRoutes():
    # list shows
    @app.route('/shows')
    def shows():
        # displays list of shows at /shows
        # TODO: replace with real venues data.
        #       num_shows should be aggregated based on number of upcoming shows per venue.
        data = [{
            "venue_id": 1,
            "venue_name": "The Musical Hop",
            "artist_id": 4,
            "artist_name": "Guns N Petals",
            "artist_image_link": "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80",
            "start_time": "2019-05-21T21:30:00.000Z"
        }]

        shows = Show.query.all()
        return render_template('pages/shows.html', shows=shows)

    # create show form

    @app.route('/shows/create')
    def create_shows():
        # renders form. do not touch.
        form = ShowForm()

        form.artist_id.choices = list(
            map(lambda artist: (artist.id, artist.name), Artist.query.all()))
        form.venue_id.choices = list(
            map(lambda venue: (venue.id, venue.name), Venue.query.all()))
        return render_template('forms/new_show.html', form=form)

    # Store Show
    @app.route('/shows/create', methods=['POST'])
    def create_show_submission():
        try:
            artist = Artist.query.get(request.form['artist_id'])
            venue = Venue.query.get(request.form['venue_id'])

            db.session.add(Show(
                artist_id=request.form['artist_id'],
                artist_name=artist.name,
                artist_image_link=artist.image_link,
                venue_id=request.form['venue_id'],
                venue_name=venue.name,
                venue_image_link=venue.image_link,
                start_time=request.form['start_time']
            ))

            db.session.commit()

            flash('show has been listed', 'success')

            return redirect(url_for('shows'))
        except Exception as error:
            db.session.rollback()

            flash('error occured: ' + error.__str__(), 'danger')

            return redirect(url_for('create_shows'))
        finally:
            db.session.close()


ShowsRoutes()


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
