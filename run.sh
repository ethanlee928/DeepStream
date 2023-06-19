#!/bin/bash

# Define DeepStream versions
declare -a ds_versions=("6.0" "6.0.1" "6.1.1" "6.2")

# Define pyds versions
declare -a pyds_versions=("1.1.1" "1.1.2" "1.1.3" "1.1.4" "1.1.5" "1.1.6")

# Prompt user to select DeepStream version
echo "Select DeepStream version:"
select ds_version in "${ds_versions[@]}"; do
    if [[ " ${ds_versions[@]} " =~ " ${ds_version} " ]]; then
        break
    else
        echo "Invalid selection. Please try again."
    fi
done

# Prompt user to select pyds version
echo "Select pyds version:"
select pyds_version in "${pyds_versions[@]}"; do
    if [[ " ${pyds_versions[@]} " =~ " ${pyds_version} " ]]; then
        break
    else
        echo "Invalid selection. Please try again."
    fi
done

# Set Docker arguments
docker_args="--build-arg DS_VERSION=${ds_version} --build-arg PYDS_VER=${pyds_version}"
docker_image="deepstream-test:DS${ds_version}-pyds${pyds_version}"

if [[ "$(docker images -q $docker_image 2> /dev/null)" == "" ]]; 
then
    # Build Docker image
    echo "Building ${docker_image} ..."
    docker build ${docker_args} -t ${docker_image} .
fi

# Run the Docker container
echo "Using ${docker_image}, starting container ..."
docker run -it --rm --gpus all --runtime nvidia \
    -e DISPLAY=${DISPLAY} -v /tmp/.X11-unix/:/tmp/.X11-unix \
    -v ${PWD}:/app/ -w /app/ ${docker_image}\
    $@
