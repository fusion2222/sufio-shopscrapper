if [ ! -d ./.venv ]; then
	echo "[+] Setting up Virtualenv..."
    virtualenv .venv
fi

source ./.venv/bin/activate
pip install -r requirements.txt
python3 ./script.py
