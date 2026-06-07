import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from zoneinfo import ZoneInfo
import bcrypt

def get_connection():
    #데이터베이스 연결
    try:
        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            ssl_ca=st.secrets["mysql"]["ssl_ca"],
            ssl_verify_cert=True,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("SET time_zone = '+09:00'")
        cursor.close()
        return conn
    except Error as e:
        st.error(f'DB 연결 실패: {e}')
        return None


@st.cache_data(ttl=600)   # ← 10분 캐싱! (메뉴는 자주 안 바뀜)
def get_menu_items(course_id):
    #특정 코스의 상세 메뉴 조회
    conn = get_connection()
    if conn is None:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT menu_name, calorie, carb, protein, fat
            FROM menu
            WHERE course_id = %s
            ORDER BY menu_id
        """, (course_id,))
        return cursor.fetchall()
    except Error as e:
        st.error(f'메뉴 조회 실패: {e}')
        return []
    finally:
        cursor.close()
        conn.close()


@st.cache_data(ttl=600)   # ← 10분 캐싱! (식단은 자주 안 바뀜)
def get_restaurant_courses(restaurant_name):
    conn = get_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        #today = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d')
        today = '2026-06-09'
        cursor.execute('''
                        SELECT c.course_id, c.course, n.total_calorie, n.total_carb, n.total_protein, n.total_fat
                        FROM course AS c JOIN nutrition AS n ON c.course_id = n.course_id
                        WHERE c.restaurant=%s AND c.date = %s
                        ORDER BY c.course_id 
                       ''', (restaurant_name, today))
        return cursor.fetchall()
    except Error as e:
        st.error(f'식단 조회 실패: {e}')
        return []
    finally:
        cursor.close()
        conn.close()


def get_restaurant_info(restaurant_name):
    autonomous_rest = ['교직원식당', '학생생활관(아람관)']
    return restaurant_name in autonomous_rest


def get_user(user_id):
    #사용자 조회
    conn = get_connection()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE user_id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        return user
    except Error as e:
        st.error(f'사용자 조회 실패: {e}')
        return None
    finally:
        cursor.close()
        conn.close()


def create_user(user_id, pin):
    conn = get_connection()
    if conn is None:
        return False
    
    try:
        # ===== PIN 해싱 =====
        pin_hash = bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt())
        
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (user_id, pin_hash, gender)
            VALUES (%s, %s, %s)
            """,
            (user_id, pin_hash.decode('utf-8'), '남성')
        )
        conn.commit()
        return True
    except Error as e:
        st.error(f'사용자 등록 실패: {e}')
        return False
    finally:
        cursor.close()
        conn.close()


def verify_pin(user_id, pin):
    user = get_user(user_id)
    if user is None:
        return False
    
    # ===== bcrypt로 PIN 검증 =====
    return bcrypt.checkpw(pin.encode('utf-8'), user['pin_hash'].encode('utf-8'))


def update_user_info(user_id, gender, age, height, weight, activity, intake, direction):
    conn = get_connection()
    if conn is None:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute('''
                        UPDATE users
                        SET gender = %s, age=%s, height=%s, weight=%s, intake=%s, direction=%s, activity=%s
                        WHERE user_id = %s
                       ''', (gender, age, height, weight, intake, direction, activity, user_id))
        conn.commit()
        return True
    except Error as e:
        st.error(f'정보 저장 실패: {e}')   # ← f-string 수정! (f 빠져있었음)
        return False
    finally:
        cursor.close()
        conn.close()