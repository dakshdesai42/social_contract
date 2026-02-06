# ⚔️ Accountability Arena

A gamified accountability app where you create challenges, compete with friends, and stay motivated through daily check-ins, streaks, and leaderboards.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- 🎯 **Create Challenges** - Set up custom challenges with your own rules
- 👥 **Invite Friends** - Share a unique code to compete together
- ✅ **Daily Check-ins** - One tap to confirm you completed the challenge
- 🔥 **Streaks** - Build consecutive day streaks for bonus points
- 🏆 **Leaderboards** - See who's winning in real-time
- 📊 **Stats Dashboard** - Track your progress over time

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or download the project**
   ```bash
   cd accountability-arena
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   python app.py
   ```

4. **Open in browser**
   ```
   http://localhost:5000
   ```

## Project Structure

```
accountability-arena/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── accountability_arena.db # SQLite database (created on first run)
├── static/
│   ├── style.css         # All styles
│   └── script.js         # Frontend JavaScript
└── templates/
    ├── base.html         # Base template
    ├── index.html        # Landing page
    ├── login.html        # Login page
    ├── register.html     # Registration page
    ├── dashboard.html    # User dashboard
    ├── challenge.html    # Challenge detail view
    ├── create_challenge.html
    ├── join_challenge.html
    ├── explore.html      # Public challenges
    └── profile.html      # User profile
```

## How It Works

### Points System
- **Base Points**: Earn points for each daily check-in (default: 10)
- **Streak Bonus**: Extra points for consecutive days (default: +5 per streak day)
- **Example**: Day 1 = 10 pts, Day 5 streak = 10 + (5×4) = 30 pts

### Creating a Challenge
1. Click "Create" in the navigation
2. Enter a name and description
3. Set point values (optional)
4. Choose if it's public or private
5. Share the generated code with friends

### Joining a Challenge
- Enter a friend's 6-character code, or
- Browse public challenges in "Explore"

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Authentication**: Session-based with Werkzeug password hashing

## Deployment

### Option 1: PythonAnywhere (Free)
1. Upload files to PythonAnywhere
2. Set up a new web app with Flask
3. Point to `app.py`

### Option 2: Render
1. Create a `render.yaml` or connect GitHub
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app.py`

### Option 3: Railway
1. Connect your GitHub repo
2. Railway auto-detects Flask
3. Deploy!

## Future Enhancements

- [ ] Email notifications for missed days
- [ ] Weekly summary reports
- [ ] Challenge end dates and winners
- [ ] Profile pictures
- [ ] Dark/light theme toggle
- [ ] Mobile app (React Native)

## Author

**Daksh Desai**
- GitHub: [@dakshdesai42](https://github.com/dakshdesai42)
- Email: ddesai35@asu.edu

## License

MIT License - feel free to use this for your own projects!
