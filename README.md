# Lumin

[![Crowdin](https://badges.crowdin.net/project-lumin/localized.svg)](https://crowdin.com/project/project-lumin)
[![GitHub Release](https://img.shields.io/github/v/release/project-lumin/closed-beta)](https://github.com/project-lumin/closed-beta/releases/latest)
![GitHub Stars](https://img.shields.io/github/stars/project-lumin/closed-beta?style=flat)
[![Discord](https://img.shields.io/discord/572077459189792769?label=discord
)](https://discord.gg/s8zBYQk)
![Top Language](https://img.shields.io/github/languages/top/project-lumin/closed-beta)
![Commit Activity](https://img.shields.io/github/commit-activity/m/project-lumin/closed-beta)

**Lumin** is a Discord bot built to replace and improve upon its predecessor, *FightMan01 bot*. It's a versatile bot featuring moderation, utility, and fun commands.

## Running the Bot

### Prerequisites

- Python **3.12+**
- **PostgreSQL**
- Recommended OS: **Linux** or **macOS** (for optimal compatibility with `uvloop`)
- The `uv` package manager

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/project-lumin/closed-beta.git
   cd lumin
   ```

2. **Create a `.env` file** in the project root (follow the `.env.example` template)

3. **Install PostgreSQL**, then:
    - Create a user named `lumin` with the password you defined above
    - Create a database named `lumin`, preferably owned by the `lumin` user
    - Optionally initialize tables by running the contents of `first_time.sql`

4. **Run the bot**
   ```bash
   uv run python -OO main.py
   ```
   `uv run` will automatically set up the virtual environment for you and download required dependencies from pyproject.toml.
   
   Python's `-OO` flag will set the `__debug__` variable to `False`, which will make the bot run in **production mode!**

   If you want to run the bot in **debug mode**, run:

   ```bash
   uv run main.py
   ```

## The difference between "production mode" and "debug mode"
When you run the bot using the regular `python main.py` command, you'll notice that the logs will say that
the bot is running in what we call "debug mode". This is because Python's built-in `__debug__` variable is
`True` by default.

Debug mode will use the `DEBUG_TOKEN` from the `.env` file and it will send automatic error reports
directly in the channel that the command was executed in.
# This is very unsafe!
Error messages might contain information that could compromise the bot.

Entering production mode will tell Python to make the `__debug__` variable `False`. It's as simple as
passing the `-O` or `-OO` flag to the Python command, like this:

```bash
python -OO main.py
```

## Using Docker

We've provided a Dockerfile and a compose file in the Github repo. You can simply run `docker compuse up --build`
to start the bot in a Docker container. Make sure to follow until step 2, because the bot still needs
the `.env` file to function properly.

## Contributor Notice

1. You're welcome to contribute via PRs — we’ll review and respond!

2. We're subclassing `commands.Context`. You’ll find this in `main.py`:
    - Import with `import main`, and use `main.Context`
    - This makes localization easier - check the docstring for details

3. The default language is **English**
    - New commands/features must include English-localized messages

4. Localization is handled via our custom package:  
   👉 [`discord-localization`](https://pypi.org/project/discord-localization)
    - Please check out our [Crowdin](https://crowdin.com/project/project-lumin) if you would like to add translations to the bot!

5. We use **NumPy-style docstrings**
    - All non-command functions should have docstrings, unless clearly self-explanatory (e.g., `load_cogs`)

6. **Helpers** are used for shared, reusable logic (e.g., `EconomyHelper` in `economy.py`)

7. For formatting, we use **custom argument classes** (e.g., `CustomUser`):
    - If you're adding a new argument class, please include a `from_X` classmethod (e.g., `CustomUser.from_user()`)
    - These help ensure editable messages are safe and intuitive (e.g., `CustomUser.avatar` returns the URL, not the raw asset)

8. Questions? DM **@pearoo** on Discord.

## Versioning & Releasing

Version numbers follow **MAJOR.MINOR.PATCH**:

- **MAJOR** → Breaking changes (e.g., full module overhauls)
    - Resets MINOR and PATCH to `0`
- **MINOR** → New features or updated command sets
    - Resets PATCH to `0`
- **PATCH** → Bugfixes, internal tweaks, or localization updates

> ⚠️ Version suffixes (e.g., `-beta`, `-dev`) will **not** be present in the live bot.
