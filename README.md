1. Create a virtual environment in the project folder:

   ```bash
   # Windows
   python -m venv venv

   # MacOS / Linux
   python3.9 -m venv venv
   ```

2. Activate the virtual environment:

   ```bash
   # Windows
   venv\Scripts\activate

   # MacOS / Linux
   source venv/bin/activate
   ```

3. Install the required libraries:

   ```bash
   pip install -r requirements.txt
   ```

---

## Start

After setting up everything, start the bot using the command:

```bash
# Windows
python -m bot.main

# MacOS / Linux
python3 -m bot.main
```