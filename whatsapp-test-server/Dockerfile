# Use a base image that comes with Puppeteer dependencies pre-installed
FROM ghcr.io/puppeteer/puppeteer:21.5.0

# Set the working directory
WORKDIR /usr/src/app

# It's good practice to run as a non-root user, but we need root to fix permissions
USER root

# Create the session data directory and change its ownership to the pptruser
# This ensures the user has permission to write to the volume mount point
RUN mkdir -p /usr/src/app/session_data && \
    chown -R pptruser:pptruser /usr/src/app/session_data

# Switch back to the non-root user to run the application securely
USER pptruser

# Copy package.json and install dependencies
COPY --chown=pptruser:pptruser package*.json ./
RUN npm install

# Copy the rest of the application code
COPY --chown=pptruser:pptruser . .

# Command to run the application
CMD [ "npm", "start" ]