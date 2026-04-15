import os
import subprocess
from datetime import datetime
from urllib.parse import urlparse

def backup_postgresql():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError('Defina DATABASE_URL para executar o backup.')
    parsed = urlparse(database_url)
    db_name = (parsed.path or '').lstrip('/') or 'database'
    backup_filename = f"backup_{db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    print(f"Iniciando backup de {db_name}...")
    
    try:
        env = os.environ.copy()
        if parsed.password:
            env['PGPASSWORD'] = parsed.password
        command = [
            'pg_dump',
            '-h', parsed.hostname or 'localhost',
            '-p', str(parsed.port or 5432),
            '-d', db_name,
            '-f', backup_filename,
        ]
        if parsed.username:
            command.extend(['-U', parsed.username])
        subprocess.run(command, check=True, env=env)
        print(f"Backup concluído: {backup_filename}")
        
        # TODO: Implementar upload para Google Drive via API
        # Requer google-api-python-client e credenciais
        print("Upload para Google Drive (Simulado)")
        
        # Limpeza local
        # os.remove(backup_filename)
        
    except Exception as e:
        print(f"Erro no backup: {e}")

if __name__ == "__main__":
    backup_postgresql()
