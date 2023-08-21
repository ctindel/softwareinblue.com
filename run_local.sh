#!/bin/bash

#!/bin/bash

# Define your image name and tag
IMAGE_NAME="sib"
IMAGE_TAG="arm"
FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"

# Check if the image exists locally
if ! docker images | grep -E "^$IMAGE_NAME\s+$IMAGE_TAG\s+"; then
    echo "Image $FULL_IMAGE not found locally. Building using docker buildx..."
    
    # Use docker buildx command here
    docker-buildx build --platform linux/arm64 -t $FULL_IMAGE .
else
    echo "Image $FULL_IMAGE is already present."
fi

docker-compose -f docker-compose.yml up sib
