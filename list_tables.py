import psycopg2
conn = psycopg2.connect('dbname=mydb user=postgres password=root host=localhost')
cur = conn.cursor()
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
for row in cur.fetchall():
    print(row[0])
