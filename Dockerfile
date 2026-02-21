# Use an official Python runtime as a parent image
# Using full image instead of slim to include build tools (like gcc) by default
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# No manual apt-get needed as the full python image includes build-essential and curl

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Create empty data files if they don't exist (because they might be in .gitignore)
# This prevents errors if the user hasn't pushed their data to GitHub.
RUN if [ ! -f portfolio.csv ]; then echo "Symbol,Current Price,Date,Time,Change,Open,High,Low,Volume,Trade Date,Purchase Price,Quantity,Commission,High Limit,Low Limit,Comment,Transaction Type" > portfolio.csv; fi
RUN if [ ! -f thesis.json ]; then echo "{}" > thesis.json; fi

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
# We use uvicorn to serve the FastAPI app. 
# Render will automatically pass the PORT env var if configured, but 8000 is our default.
CMD ["sh", "-c", "uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
