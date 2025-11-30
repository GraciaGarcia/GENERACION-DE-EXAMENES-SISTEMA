import os

wallet_path = os.path.abspath("Wallet_developer")
os.environ["TNS_ADMIN"] = wallet_path 

SQLALCHEMY_DATABASE_URI = (
    f"oracle+oracledb://BANCO_PREGUNTAS:ValleGrande_2025"
    f"@/?wallet_location={wallet_path}&dsn=proyecto_medium"
)

FLASK_RUN_PORT = 5000
