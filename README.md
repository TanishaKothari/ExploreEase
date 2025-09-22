# EXPLORE EASE

## Description
Explore Ease is a web application designed to help users create personalized travel itineraries based on their preferences, budget, and travel goals. The application uses the OpenAI Groq API to generate itineraries based on user input.

## Table of Contents
1. Features
2. Installation
3. Usage
4. Database Structure
5. API Integration
6. Code Structure

## Features
- User Authentication
- Personalized travel itinerary generation based on user input
- Save, view and delete saved itineraries
- Provide and view feedback on generated itineraries
- Edit user profile
- Delete user account and all associated data

## Installation
1. Clone this repository: https://github.com/TanishaKothari/explore-ease.git
2. Navigate to the project directory: `cd explore-ease`
3. Install the required dependencies: `pip install -r requirements.txt`
4. Run the application: `python app.py`
5. The .env file stores the API key and database connection details.

## Usage
1. Acess the live web application at [ExploreEase](https://exploreease-w7ps.onrender.com/login).
2. Register an account by clicking the "Register" link and providing a valid username and password.
3. Log in to your account using the details provided during the registration.
4. Fill out the travel preferences form to generate a personalized travel itinerary.
5. Generate a new itinerary with the same inputs using the "Regenerate" button, save the generated itinerary using the "Save Plan" button, or provide feedback on the generated itinerary by clicking the "Give feedback" button and filling out the feedback form.
6. View all saved itineraries in the "Saved Itineraries" section. Unsave itineraries by clicking the "Delete" button.
7. Edit your profile or delete account by clicking on your username and selecting "Edit Profile".
8. Logout by clicking on your username and selecting "Logout".

## Database Structure
The application uses a PostgreSQL database to store user information and user input. The database contains the following tables:
- users: Stores user information such as the user's ID, username and hashed password.
- user_input: Stores user input entered in the itinerary generation form until the user logs out.
- saved_plans: Stores saved itineraries with user ID and plan ID.
- feedback: Stores user feedback along with feedback's ID and user ID.

## API Integration
The application integrates with the OpenAI Groq API to generate personalized travel itineraries based on user input. The API is used to create a custom AI agent and task, which in turn generates the itinerary based on the provided criteria.

## Code Structure
The application is built using the Flask framework in Python. The code is organized into multiple files, including:
- app.py: The main Flask application file, which contains the routes, views, and functions for the web application.
- templates/: A directory containing all the HTML templates used by the application.
- static/: A directory containing the CSS file.


