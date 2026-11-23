#!/bin/bash
# Build lambda.zip for the EuroLeague weekly pipeline.
# Run from the project folder:  bash build_lambda.sh
# (Run it as a file. Don't paste these lines into Terminal one by one.)
set -e

echo "1/5 Cleaning old build..."
rm -rf build lambda.zip
mkdir build

echo "2/5 Installing pure-Python libraries..."
pip install euroleague-api xmltodict --no-deps --target build --quiet

echo "3/5 Installing Linux versions of requests and tqdm for Lambda (Python 3.12)..."
pip install requests tqdm \
  --target build \
  --platform manylinux2014_x86_64 \
  --python-version 3.12 \
  --implementation cp \
  --only-binary=:all: \
  --quiet

echo "4/5 Copying pipeline code..."
cp pipeline/handler.py build/
cp transform/transform.py build/
cp quality/checks.py build/

echo "5/5 Zipping..."
cd build
zip -r ../lambda.zip . -q
cd ..

grep -qxF "build/" .gitignore || echo "build/" >> .gitignore
grep -qxF "lambda.zip" .gitignore || echo "lambda.zip" >> .gitignore

echo ""
echo "Check: these files must be in the zip:"
unzip -l lambda.zip | grep -E " (handler|transform|checks|xmltodict)\.py$"
echo ""
ls -lh lambda.zip
