$env:KMP_DUPLICATE_LIB_OK = "TRUE"
$env:PYTHONPATH = "."
& "C:\Users\leomo\anaconda3\envs\data\python.exe" -m unittest tests/test_dashboard.py -v
