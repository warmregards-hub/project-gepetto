FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source code
COPY . .

# Build-time env vars (Vite bakes these in at build time)
ARG VITE_ELEVENLABS_AGENT_ID
ENV VITE_ELEVENLABS_AGENT_ID=$VITE_ELEVENLABS_AGENT_ID

# Build for production preview
RUN npm run build

# Expose port
EXPOSE 5173

# Start preview server
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
