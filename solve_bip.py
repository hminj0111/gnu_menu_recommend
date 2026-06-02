from pulp import *
from datetime import datetime
import streamlit as st
from mysql.connector import Error
from zoneinfo import ZoneInfo
from db_connect import get_connection

autonomous_rest = ['교직원식당','학생생활관(아람관)']
intake_map = {'적게':0.7, '보통':1.0, '많이':1.5}
constraints = {
    '균형': {
        'carb': (0.55, 0.65),
        'protein': (0.07, 0.20),
        'fat': (0.15, 0.30)
    },
    '저탄수': {
        'carb': (0.30, 0.50),
        'protein': (0.20, 0.30),
        'fat': (0.40, 0.60)
    },
    '고단백': {
        'carb': (0.40, 0.50),
        'protein': (0.25, 0.35),
        'fat': (0.20, 0.30)
    }
}

#개인 목표 열량 계산
def calculate_calorie(gender, weight, height, age, activity_factor):
    activity_map = {
    '운동 안 함': 1.2,
    '가벼운 운동': 1.375,
    '보통 운동': 1.55,
    '활발한 운동': 1.725,
    '매우 활발한 운동': 1.9
    }
    if gender == '남성':
        bmr = 10*weight+6.25*height-5*age+5
    else:
        bmr = 10*weight+6.25*height-5*age-161

    tdee = bmr*activity_map[activity_factor] #tdee:일일 총 에너지 소비량
    target_calorie = tdee*0.4 #일일 총 에너지 소비량의 40%를 점심을 이용해 섭취

    return bmr, tdee, target_calorie #개인목표열량에서 보여줄 내용 및 target_calorie 는 이진정수계획법에서 사용

#식단 정보 조회
def get_meals(conn):
    cursor = conn.cursor(dictionary=True)
    today = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d') #대한민국 시간으로 저장하도록 설정해둠
    
    cursor.execute('''
                SELECT c.course_id, c.date, c.restaurant, c.course, n.total_calorie AS calorie,n.total_carb AS carb, n.total_protein AS protein, n.total_fat AS fat 
                FROM course AS c JOIN nutrition AS n ON (c.course_id=n.course_id) 
                WHERE c.date = %s
                   ''', (today,))
    meals = cursor.fetchall()
    cursor.close()
    return meals

#식당별 섭취량 배수 계산
def get_r_list(meals, intake):
    r_list = []
    for m in meals:
        if m['restaurant'] in autonomous_rest:
            r_list.append(intake_map[intake])
        else:
            r_list.append(1.0)
    return r_list

def solve_bip(meals, target_calorie, direction, r_list, excluded=[]):
    prob = LpProblem('meal_recommendation', LpMinimize)

    x = [LpVariable(f"x_{m['course_id']}", cat='Binary') for m in meals]
    d = LpVariable('d', lowBound=0)
    prob += d

    total_calorie = lpSum(m['calorie'] * x[i] * r_list[i] for i, m in enumerate(meals))
    prob += d >= total_calorie - target_calorie
    prob += d >= target_calorie - total_calorie
    prob += lpSum(x) == 1

    # ===== Integer Cut: 이미 선택된 식단 제외 =====
    for course_id in excluded:
        for i, m in enumerate(meals):
            if m['course_id'] == course_id:
                prob += x[i] == 0

    con = constraints[direction]
    total_carb_kcal = lpSum(m['carb'] * 4 * x[i] * r_list[i] for i, m in enumerate(meals))
    total_protein_kcal = lpSum(m['protein'] * 4 * x[i] * r_list[i] for i, m in enumerate(meals))
    total_fat_kcal = lpSum(m['fat'] * 9 * x[i] * r_list[i] for i, m in enumerate(meals))

    prob += total_carb_kcal >= con['carb'][0] * target_calorie
    prob += total_carb_kcal <= con['carb'][1] * target_calorie
    
    prob += total_protein_kcal >= con['protein'][0] * target_calorie
    prob += total_protein_kcal <= con['protein'][1] * target_calorie

    prob += total_fat_kcal >= con['fat'][0] * target_calorie
    prob += total_fat_kcal <= con['fat'][1] * target_calorie

    prob.solve(PULP_CBC_CMD(msg=0))
    return prob.status, x, d

def solve_bip_step3(meals, target_calorie, r_list, excluded=[]):
    prob = LpProblem('meal_recommendation_step3', LpMinimize)

    x = [LpVariable(f"x_{m['course_id']}", cat='Binary') for m in meals]
    d = LpVariable('d', lowBound=0)
    prob += d

    total_calorie = lpSum(m['calorie'] * x[i] * r_list[i] for i, m in enumerate(meals))
    prob += d >= total_calorie - target_calorie
    prob += d >= target_calorie - total_calorie
    prob += lpSum(x) == 1

    # ===== Integer Cut =====
    for course_id in excluded:
        for i, m in enumerate(meals):
            if m['course_id'] == course_id:
                prob += x[i] == 0

    prob.solve(PULP_CBC_CMD(msg=0))
    return prob.status, x, d

#결과출력 recommend 함수 실행 시 return 값 형태 결정
def get_result(meals, x, d, target_calorie, step):
    for i, m in enumerate(meals):
        if value(x[i]) == 1:
            return{
                'step':step,
                'meal':m,
                'target_calorie': round(target_calorie, 1),
                'diff': round(value(d),1)
            } #fallback 단계(1,2,3), 선택된 식단, 목표 칼로리, 차이 값 딕셔너리 형태로 반환

#fallback 구조 ==> 해당 부분 streamlit 구조에 맞게 수정 필요함. streamlit 고려하지 않고 작성해둔 상태
def recommend(conn, gender, weight, height, age, intake, direction, activity_factor):
    intake_map = {
    '적게':0.7,
    '보통':1.0,
    '많이':1.5
    }    
    meals = get_meals(conn)
    bmr, tdee, target_calorie = calculate_calorie(gender, weight, height, age, activity_factor)
    

    #step1: 섭취방향 반영(저탄수, 밸런스, 고단백)
    status, x, d = solve_bip(meals, target_calorie, direction, intake)
    if status==1:
        return get_result(meals, x, d, target_calorie, step=1)
    
    #step2: 밸런스 기본 비율 적용
    status, x, d = solve_bip(meals, target_calorie, '균형', intake)
    if status==1:
        return get_result(meals, x, d, target_calorie, step=2)
    
    #step3: 영양소 제약조건 제거(영양성분과 관련된 제약없이 목표 칼로리와 섭취 칼로리 차이를 최소화)
    prob = LpProblem('meal_recommendation_step3', LpMinimize)
    x = [LpVariable(f"x_{m['course_id']}", cat='Binary') for m in meals]
    autonomous_rest = ['교직원식당','학생생활관(아람관)']
    r_list = []
    for m in meals:
        if m['restaurant'] in autonomous_rest:
            r_list.append(intake_map[intake])
        else:
            r_list.append(1.0)

    d=LpVariable('d', lowBound=0)
    prob += d
    total_calorie = lpSum(m['calorie']*x[i]*r_list[i] for i, m in enumerate(meals))
    prob += d >= total_calorie-target_calorie #실제 칼로리가 목표보다 높은 경우
    prob += d >= target_calorie-total_calorie #실제 칼로리가 목표보다 낮은 경우
    prob += lpSum(x)==1
    prob.solve(PULP_CBC_CMD(msg=0))
    return get_result(meals, x, d, target_calorie, step=3)

def get_result(meals, x, d, target_calorie, step):
    for i, m in enumerate(meals):
        if value(x[i])==1:
            return{
                'step':step,
                'meal':m,
                'target_calorie': round(target_calorie, 1),
                'diff': round(value(d), 1)
            }

def recommend(conn, gender, weight, height, age, intake, direction, activity_factor):
    meals = get_meals(conn)
    if not meals:
        return []
    bmr, tdee, target_calorie = calculate_calorie(gender, weight, height, age, activity_factor)
    r_list = get_r_list(meals, intake)

    results = []
    excluded = []

    for _ in range(2):
        status, x, d = solve_bip(meals, target_calorie, direction, r_list, excluded)
        if status == 1:
            result = get_result(meals, x, d, target_calorie, step=1)
            if result:
                results.append(result)
                excluded.append(result['meal']['course_id'])
        else:
            break
    if not results:
        for _ in range(2):
            status, x, d = solve_bip(meals, target_calorie, '균형', r_list, excluded)
            if status == 1:
                result = get_result(meals, x, d, target_calorie, step=2)
                if result:
                    results.append(result)
                    excluded.append(result['meal']['course_id'])
            else:
                break
    if not results:
        for _ in range(2):
            status, x, d = solve_bip_step3(meals, target_calorie, r_list, excluded)
            if status == 1:
                result = get_result(meals, x, d, target_calorie, step=3)
                if result:
                    results.append(result)
                    excluded.append(result['meal']['course_id'])
            else:
                break

    return results