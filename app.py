from flask import Flask, render_template, request, redirect, url_for, flash
from database import init_db, get_db_connection
import re

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Инициализация БД при запуске
init_db()

def validate_phone(phone):
    """Проверка корректности номера телефона"""
    phone = re.sub(r'\D', '', phone)
    if len(phone) == 11 and phone.startswith(('7', '8')):
        return '7' + phone[1:]
    return None

@app.route('/')
def index():
    return redirect(url_for('clients'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_phones():
    if request.method == 'POST':
        phones_text = request.form.get('phones', '')
        phones_list = phones_text.strip().split('\n')
        
        added_count = 0
        conn = get_db_connection()
        
        for phone in phones_list:
            phone = phone.strip()
            if not phone:
                continue
                
            validated_phone = validate_phone(phone)
            if validated_phone:
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        'INSERT OR IGNORE INTO clients (phone) VALUES (?)',
                        (validated_phone,)
                    )
                    if cursor.rowcount > 0:
                        added_count += 1
                except sqlite3.IntegrityError:
                    continue
        
        conn.commit()
        conn.close()
        
        flash(f'Успешно добавлено {added_count} номеров!', 'success')
        return redirect(url_for('clients'))
    
    return render_template('upload.html')

@app.route('/clients')
def clients():
    status_filter = request.args.get('status', '')
    
    conn = get_db_connection()
    
    if status_filter:
        clients = conn.execute(
            'SELECT * FROM clients WHERE status = ? ORDER BY created_at DESC',
            (status_filter,)
        ).fetchall()
    else:
        clients = conn.execute(
            'SELECT * FROM clients ORDER BY created_at DESC'
        ).fetchall()
    
    # Получаем статистику по статусам
    status_stats = conn.execute('''
        SELECT status, COUNT(*) as count 
        FROM clients 
        GROUP BY status
    ''').fetchall()
    
    conn.close()
    
    return render_template('clients.html', 
                         clients=clients, 
                         status_stats=status_stats,
                         current_status=status_filter)

@app.route('/client/<int:client_id>', methods=['GET', 'POST'])
def edit_client(client_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form.get('name', '')
        services = request.form.get('services', '')
        deadline = request.form.get('deadline', '')
        budget = request.form.get('budget', '')
        status = request.form.get('status', 'Новый')
        
        # Преобразуем бюджет в число, если он указан
        try:
            budget = int(budget) if budget else None
        except ValueError:
            budget = None
        
        conn.execute('''
            UPDATE clients 
            SET name = ?, services = ?, deadline = ?, budget = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, services, deadline, budget, status, client_id))
        
        conn.commit()
        conn.close()
        
        flash('Данные клиента обновлены!', 'success')
        return redirect(url_for('clients'))
    
    client = conn.execute('SELECT * FROM clients WHERE id = ?', (client_id,)).fetchone()
    conn.close()
    
    if client is None:
        flash('Клиент не найден!', 'error')
        return redirect(url_for('clients'))
    
    return render_template('edit_client.html', client=client)

@app.route('/delete_client/<int:client_id>')
def delete_client(client_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM clients WHERE id = ?', (client_id,))
    conn.commit()
    conn.close()
    
    flash('Клиент удален!', 'success')
    return redirect(url_for('clients'))

# Список возможных статусов
STATUSES = [
    'Новый',
    'В работе',
    'Консультация',
    'Ожидание ответа',
    'Сделка заключена',
    'Отказ',
    'Завершен'
]

@app.context_processor
def utility_processor():
    return dict(statuses=STATUSES)

if __name__ == '__main__':
    app.run(debug=True)