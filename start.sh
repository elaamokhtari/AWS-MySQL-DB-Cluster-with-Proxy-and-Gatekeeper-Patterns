# Activate the virtual environment
source log8415_lab3/bin/activate

# Install dependencies
pip install -r requirements.txt

# Navigate to the infrastructure directory
cd infrastructure

# Execute infrastructure setup
python3 aws_infrastructure.py

# navigate to the benchmark directory
cd ../benchmark

# Run benchmark tests
python3 benchmark.py

