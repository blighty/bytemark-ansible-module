#!/bin/sh

LANG=python

# Generate python APIs from swagger spec files
docker run --rm -v ${PWD}:/local swaggerapi/swagger-codegen-cli generate -i /local/specs/authorization/authorization.yml \
-l $LANG -c /local/specs/authorization/config.json -o /local/generated/bytemark-authorization

docker run --rm -v ${PWD}:/local swaggerapi/swagger-codegen-cli generate -i /local/specs/cloud/cloud.yml \
-l $LANG -c /local/specs/cloud/config.json -o /local/generated/bytemark-cloud

# Install virtualenv pip package
pip install virtualenv

# Create a python virtual environment if it doesn't exist
if [ ! -d env ]; then
  virtualenv env
fi

# Install python APIs inside the python virtual environment
source env/bin/activate

cd generated/bytemark-authorization
sudo python setup.py install

cd ../bytemark-cloud
sudo python setup.py install
