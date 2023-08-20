import pyodbc


class GradeDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db_connection = None
        self.cursor = None
        self.connect(db_path)

    def connect(self, db_path):
        try:
            self.db_connection = pyodbc.connect(r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + db_path)
            self.cursor = self.db_connection.cursor()
            print("Veritabanı bağlantısı başarılı.")
        except pyodbc.Error as e:
            print("Veritabanı bağlantısı hatası:", str(e))

    def close(self):
        self.cursor.close()
        self.db_connection.close()

    def is_table_exist(self, table_name):
        if self.db_connection:
            existing_tables = [table.table_name for table in self.cursor.tables(tableType='TABLE')]
            return table_name in existing_tables

    def is_table_empty(self, table_name):
        row_count = 0
        if self.is_table_exist(table_name):
            self.cursor.execute(f'SELECT COUNT(*) FROM [{table_name}]')
            row_count = self.cursor.fetchone()[0]
        return row_count == 0

    def create_semester_table(self, semester):
        if self.db_connection:
            try:
                if not self.is_table_exist(semester):
                    create_table_query = f"""
                    CREATE TABLE [{semester}] (
                        id AUTOINCREMENT PRIMARY KEY,
                        student_id INT,
                        lesson_name TEXT,
                        midterm_grade TEXT,
                        final_grade TEXT,
                        makeup_grade TEXT,
                        letter_grade TEXT,
                        midterm_mail_sent BIT,
                        final_mail_sent BIT,
                        makeup_mail_sent BIT,
                        letter_grade_mail_sent BIT
                    )
                    """
                    print(create_table_query)
                    self.cursor.execute(create_table_query)
                    self.db_connection.commit()
            except Exception as e:
                self.db_connection.rollback()
                print("An error occurred while creating the semester table:", e)

    def insert_grades_to_database(self, semester, lesson_data):
        if self.db_connection:
            try:
                if self.is_table_empty(semester):
                    for lesson in lesson_data:
                        print(lesson)
                        insert_query = f"""
                                INSERT INTO "{semester}" (lesson_name, student_id, midterm_grade, final_grade, 
                                makeup_grade, letter_grade, midterm_mail_sent, final_mail_sent, makeup_mail_sent, 
                                letter_grade_mail_sent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                        self.cursor.execute(insert_query, (lesson['lesson_name'], 200503304, lesson['midterm_grade'],
                                                           lesson['final_grade'], lesson['makeup_grade'],
                                                           lesson['letter_grade'],
                                                           0, 0, 0, 0))
                        self.db_connection.commit()

            except Exception as e:
                self.db_connection.rollback()
                print("An error occurred while inserting grades:", e)

    def fetch_grades_from_database(self, semester):
        if self.db_connection:
            try:
                select_query = f"""
                    SELECT lesson_name, midterm_grade, final_grade, makeup_grade, letter_grade FROM "{semester}" """
                self.cursor.execute(select_query)
                lesson_data = self.cursor.fetchall()
                return lesson_data
            except Exception as e:
                print("An error occurred while fetching grades", e)

    def update_current_semester_table(self):
        if self.db_connection:
            print("dad")


