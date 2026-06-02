import streamlit as st
import mysql.connector
from pulp import *
from datetime import date
from db_connect import get_connection, get_menu_items, get_restaurant_courses, get_user, create_user,verify_pin, update_user_info
from solve_bip import recommend, calculate_calorie
import plotly.graph_objects as go

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "is_new_user" not in st.session_state:
    st.session_state.is_new_user = False
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False

# 저장된 사용자 정보 초기값 (None)
if "saved_gender" not in st.session_state:
    st.session_state.saved_gender = None
if "saved_age" not in st.session_state:
    st.session_state.saved_age = None
if "saved_height" not in st.session_state:
    st.session_state.saved_height = None
if "saved_weight" not in st.session_state:
    st.session_state.saved_weight = None
if "saved_activity" not in st.session_state:
    st.session_state.saved_activity = None
if "saved_intake" not in st.session_state:
    st.session_state.saved_intake = None
if "saved_direction" not in st.session_state:
    st.session_state.saved_direction = None
#UI - streamlit 이용

#페이지 설정
st.set_page_config(page_title='가좌캠퍼스 식단 추천', page_icon='🍱', layout='wide')

#로그인 화면
if not st.session_state.logged_in:
    login_placeholder = st.empty()

    with login_placeholder.container():
        col_left, col_center, col_right = st.columns([1,2,1])

        with col_center:
            col_logo, col_title = st.columns([1,4], vertical_alignment='center')
            with col_logo:
                st.image('image/gnu_character2.png', width=100)
            with col_title:
                st.title('가좌캠퍼스 식단 추천 시스템')
            st.divider()

            #로그인 폼
            st.subheader('🔐 로그인')
            st.caption('학번/사번과 PIN 4자리를 입력해주세요. 처음이라면 자동으로 등록됩니다.')

            user_id_input = st.text_input('학번/사번', max_chars=10, placeholder='학번(사번)')
            pin_input = st.text_input('PIN (4자리 숫자)', max_chars=4, type='password', placeholder='••••')
            login_clicked = st.button('로그인', type = 'primary', width='stretch')
            guest_clicked = st.button('비회원으로 사용하기', type = 'tertiary',width='stretch', key='guest_login')
            st.markdown("""
                        <style>

                        div.stButton > button[kind="secondary"] {
                            border: none;
                            background: none;
                            color: #aaaaaa;
                            font-size: 12px;
                            padding: 0;
                            margin: 0;
                            min-height: auto;
                        }

                        div.stButton > button[kind="secondary"]:hover {
                            color: #666666;
                            text-decoration: underline;
                        }

                        </style>
                        """, unsafe_allow_html=True)

    # 오른쪽 정렬용 컬럼
            left, right = st.columns([8, 2])

            with right:
                forgot_clicked = st.button(
                    "PIN을 잊으셨나요?",
                    type="secondary"
                )
            # 로그인 처리
            if login_clicked:
                # 입력 검증
                if not user_id_input or not pin_input:
                    st.error("⚠️ 학번/사번과 PIN을 모두 입력해주세요.")
                elif len(pin_input) != 4 or not pin_input.isdigit():
                    st.error("⚠️ PIN은 4자리 숫자여야 합니다.")
                else:
                    user = get_user(user_id_input)
                    if user is None:
                        success = create_user(user_id_input, pin_input)
                        if success:
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_id_input
                            st.session_state.is_new_user = True
                            st.rerun()
                        else:
                            st.error('등록 중 오류가 발생했습니다.')
                    else: #기존 사용자
                        if verify_pin(user_id_input, pin_input):
                            login_placeholder.empty()
                            st.session_state.logged_in = True
                            st.session_state.user_id = user_id_input
                            st.session_state.is_new_user = False

                            user = get_user(user_id_input)
                            st.session_state.saved_gender = user['gender']
                            st.session_state.saved_age = user['age']
                            st.session_state.saved_height = user['height']
                            st.session_state.saved_weight = user['weight']
                            st.session_state.saved_activity = user['activity']
                            st.session_state.saved_intake = user['intake']
                            st.session_state.saved_direction = user['direction']
                            
                            st.rerun()
                        else:
                            st.error('PIN이 일치하지 않습니다. 다시 입력해주세요.')
        if guest_clicked:
            login_placeholder.empty()
            st.session_state.logged_in = True
            st.session_state.user_id = None
            st.session_state.is_guest = True
            st.rerun()

        # PIN 분실 안내
        if forgot_clicked:
            st.info(
                "PIN 분실 시 시스템 관리자에게 문의해주세요."
            )


#사이드바 (정보 입력 부분) 
else: 
    with st.sidebar:
        st.header('기본 정보 입력')
        gender_options = ['남성','여성']
        gender_index = gender_options.index(st.session_state.saved_gender) if st.session_state.saved_gender else 0
        gender = st.radio("성별", gender_options, index=gender_index)

        age = st.number_input(
            '나이(만 나이)',
            min_value=0, max_value=100,step=1,
            value=st.session_state.saved_age, placeholder='나이를 입력하세요.'
        ) #step --> 값을 어떻게 입력받을 지,,, 나이의 경우 정수로
        
        height = st.number_input(
            '키 (cm)',
            min_value=1.0, max_value=220.0,step=0.1,
            value=float(st.session_state.saved_height) if st.session_state.saved_height else None, 
            placeholder='키를 입력하세요.', format='%.1f'
        ) 

        weight = st.number_input(
            '체중 (kg)',
            min_value=1.0, max_value=250.0,step=0.1,
            value=float(st.session_state.saved_weight) if st.session_state.saved_weight else None,
            placeholder='몸무게를 입력하세요.', format='%.1f'
        )

        st.divider()
        activity_options = ["운동 안 함", "가벼운 운동", "보통 운동", "활발한 운동", "매우 활발한 운동"]
        activity_index = activity_options.index(st.session_state.saved_activity) if st.session_state.saved_activity else 1
        activity = st.radio(
            "활동량",
            activity_options,
            index=activity_index,
            captions=["좌식 생활 위주", "주 1~3회", "주 3~5회", "주 6~7회", "매일 격한 운동"]
        )
        
        # 섭취량
        intake_options = ["적게", "보통", "많이"]
        intake_index = intake_options.index(st.session_state.saved_intake) if st.session_state.saved_intake else 1
        intake = st.radio("섭취량", intake_options, index=intake_index, horizontal=True)
        
        # 섭취 방향
        direction_options = ["균형", "저탄수", "고단백"]
        direction_index = direction_options.index(st.session_state.saved_direction) if st.session_state.saved_direction else 0
        direction = st.radio("섭취 방향", direction_options, index=direction_index, horizontal=True)

        calculate = st.button('🔥식단 추천🔥', type='primary', width='stretch')

    #메인영역 
    col_logo,col_title, col_login = st.columns([1,6,2], vertical_alignment='center')
    with col_logo:
        st.image('image/gnu_character2.png', width='stretch')
    with col_title:
        st.title('가좌캠퍼스 식단 추천 시스템')
    with col_login:
        if st.session_state.is_guest:
            st.markdown('**비회원**')
            if st.button('로그인', width='stretch', key='guest_to_login'):
                st.session_state.logged_in = False
                st.session_state.is_guest = False
                st.rerun()
        else:
            st.markdown(f'**{st.session_state.user_id}** 님')
            if st.button('로그아웃', width='stretch', key='logout_button'):
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.is_guest = False
                st.rerun()

    st.caption('ℹ️ 본 시스템의 영양정보는 공공데이터(식약처 식품영양성분 DB)를 기반으로 계산되어 실제와 차이가 있을 수 있습니다.') #실제와 차이가 있음을 공지


        
    st.divider()
    tab1, tab2, tab3 = st.tabs([
        '📊 개인 목표 열량',
        '🎯 추천 결과',
        '🍽️ 전체 식단 영양정보'
    ])

    with tab1:
        st.header('📊 개인 목표 열량')
        if calculate: #계산하기 버튼을 눌렀을 때
            if age is None or height is None or weight is None: #필수 정보 미 기입 시 에러 발생
                st.error('⚠️사이드바의 모든 항목을 입력해주세요⚠️')
            
            else: #필수 정보 기입 시 목표 칼로리 계산
                bmr, tdee, target_calorie = calculate_calorie(gender, weight, height, age, activity)

                if not st.session_state.is_guest:
                    update_user_info(st.session_state.user_id, gender, age, height, weight, activity,
                                     intake, direction)
                col_a, col_b, col_c = st.columns(3) #기초대사량 및 tdee, 점심 목표 칼로리 출력
                with col_a:
                    st.metric('기초대사량 (BMR)', f'{bmr:.0f} kcal')
                with col_b:
                    st.metric('일일 권장 섭취량 (TDEE)', f'{tdee:.0f} kcal')
                with col_c:
                    st.metric('점심 목표 칼로리', f'{target_calorie:.0f} kcal')
                st.divider()


        else: #계산하기 버튼을 누르지 않았을 때
            st.info('👈왼쪽 사이드바에서 정보를 입력해주세요!')

    with tab2:
        st.header('🎯 추천 결과')
        
        tab2_placeholder = st.empty()   # placeholder 생성
        
        if calculate:
            if age is None or height is None or weight is None:
                with tab2_placeholder.container():
                    st.error('⚠️사이드바의 모든 항목을 입력해주세요⚠️')
            else:
                tab2_placeholder.empty()   # 기존 내용 즉시 제거!
                
                conn = get_connection()
                if conn is None:
                    st.error('⚠️DB 연결에 실패했습니다⚠️')
                else:
                    try:
                        results = recommend(conn, gender, weight, height, age, intake, direction, activity)
                        
                        with tab2_placeholder.container():
                            if not results:
                                st.warning('⚠️ 오늘 추천 가능한 식단이 없습니다')
                            else:
                                # fallback 단계 안내 (첫 번째 결과 기준)
                                step = results[0]['step']
                                if step == 1:
                                    st.success(f'✅ {direction} 모드의 영양 비율 조건을 만족하는 최적의 식단을 추천해드려요.')
                                elif step == 2:
                                    st.info(f'ℹ️ {direction} 모드에 적합한 식단이 없어, "균형 비율"로 추천해드려요.')
                                else:
                                    st.warning('⚠️ 오늘은 영양 비율을 맞추기 어려워, "칼로리 기준"으로만 추천했어요.')

                                st.write('')

                                direction_ratio = {
                                    '균형': {'carb': (0.55,0.65), 'protein': (0.07,0.20), 'fat': (0.15,0.30)},
                                    '저탄수': {'carb': (0.30,0.50), 'protein': (0.20,0.30), 'fat': (0.40,0.60)},
                                    '고단백': {'carb': (0.40,0.50), 'protein': (0.25,0.35), 'fat': (0.20,0.30)}
                                }

                                # ===== 추천 결과 루프 =====
                                for idx, result in enumerate(results):
                                    meal = result['meal']
                                    step_i = result['step']
                                    target_calorie = result['target_calorie']

                                    # ===== 변수 정의 (루프 맨 위) =====
                                    actual_cal = meal['calorie']
                                    actual_carb = meal['carb']
                                    actual_protein = meal['protein']
                                    actual_fat = meal['fat']

                                    carb_cal = actual_carb * 4
                                    protein_cal = actual_protein * 4
                                    fat_cal = actual_fat * 9

                                    actual_carb_ratio = (carb_cal / actual_cal) * 100
                                    actual_protein_ratio = (protein_cal / actual_cal) * 100
                                    actual_fat_ratio = (fat_cal / actual_cal) * 100
                                    diff = actual_cal - target_calorie

                                    # 추천 순위 (2개일 때만)
                                    if len(results) > 1:
                                        st.markdown(f'### {"1️⃣" if idx == 0 else "2️⃣"} 추천 {"1" if idx == 0 else "2"}순위') #식단이 1개만 존재하는 경우엔 바로 식단 정보와 그래프 뜨도록

                                    # ===== 식단카드 + 그래프 좌우 배치 =====
                                    col_left, col_right = st.columns([1, 1])

                                    # ===== 왼쪽: 식단 카드 =====
                                    with col_left:
                                        with st.container(border=True):
                                            col_rest, col_course = st.columns([1, 1])
                                            with col_rest:
                                                st.markdown('📍식당')
                                                st.markdown(f'{meal["restaurant"]}')
                                            with col_course:
                                                st.markdown('🍽️식단명')
                                                st.markdown(f'{meal["course"]}')

                                            st.divider()
                                            st.markdown('상세 메뉴')
                                            menu_items = get_menu_items(meal['course_id'])

                                            if menu_items:
                                                for item in menu_items:
                                                    st.markdown(f"- {item['menu_name']}")
                                            else:
                                                st.caption('세부 메뉴 정보가 없습니다.')

                                    # ===== 오른쪽: 그래프 =====
                                    with col_right:
                                        if step_i == 3:
                                            st.header('탄단지 비율')
                                            # Step 3: 탄단지 비율 세로 막대
                                            fig = go.Figure(data=[
                                                go.Bar(
                                                    x=['탄수화물', '단백질', '지방'],
                                                    y=[actual_carb_ratio, actual_protein_ratio, actual_fat_ratio],
                                                    marker=dict(
                                                        color=['#FF6B6B', '#FFABAB', '#FF8C8C'],
                                                        line=dict(color='rgba(0,0,0,0)', width=0)
                                                    ),
                                                    text=[f'{actual_carb_ratio:.0f}%',
                                                        f'{actual_protein_ratio:.0f}%',
                                                        f'{actual_fat_ratio:.0f}%'],
                                                    textposition='outside',
                                                    hovertemplate='<b>%{x}</b><br>%{y:.1f}%<extra></extra>',
                                                    width=0.4
                                                )
                                            ])
                                            fig.update_layout(
                                                height=300,
                                                showlegend=False,
                                                yaxis_title='비율 (%)',   # ← g → %로 변경!
                                                xaxis_title='',
                                                margin=dict(l=50, r=50, t=30, b=50),
                                                template='plotly_white',
                                                font=dict(family='Arial, sans-serif', size=12),
                                                hovermode='x unified'
                                            )
                                            st.plotly_chart(fig, width='stretch', key=f'tab2_nutrition_{idx}')

                                        else:
                                            st.header('탄단지 비율 목표 달성도')
                                            st.caption('회색 범위: 목표 비율 범위(일일 권장 섭취량 기준) \n\n빨간 선: 실제 비율(실제 점심 섭취량 기준)')

                                            # Step 1/2: 탄단지 비율 목표 달성도 가로 막대
                                            if step_i == 2:
                                                goal = direction_ratio['균형']
                                            else:
                                                goal = direction_ratio[direction]

                                            fig = go.Figure()
                                            fig.add_trace(go.Bar(
                                                y=['지방', '단백질', '탄수화물'],
                                                x=[goal['fat'][1]*100 - goal['fat'][0]*100,
                                                   goal['protein'][1]*100 - goal['protein'][0]*100,
                                                   goal['carb'][1]*100 - goal['carb'][0]*100],
                                                base=[goal['fat'][0]*100, goal['protein'][0]*100, goal['carb'][0]*100],
                                                orientation='h',
                                                marker_color='#e0e0e0',
                                                name='목표 범위',
                                                hovertemplate='<b>%{y}</b><br>목표: %{base:.0f}% ~ %{x:.0f}%<extra></extra>',
                                                showlegend=True
                                            ))
                                            fig.add_trace(go.Bar(
                                                y=['지방', '단백질', '탄수화물'],
                                                x=[1.0, 1.0, 1.0],
                                                base=[actual_fat_ratio - 0.25,
                                                      actual_protein_ratio - 0.25,
                                                      actual_carb_ratio - 0.25],
                                                orientation='h',
                                                marker_color='#ff4b4b',
                                                name='내 식단 실제 비율',
                                                text=[f'{actual_fat_ratio:.0f}%',
                                                      f'{actual_protein_ratio:.0f}%',
                                                      f'{actual_carb_ratio:.0f}%'],
                                                textposition='outside',
                                                hovertemplate='<b>%{y}</b><br>실제: %{base:.0f}%<extra></extra>',
                                                showlegend=True
                                            ))
                                            fig.update_layout(
                                                barmode='overlay',
                                                height=300,
                                                showlegend=True,
                                                xaxis_title='비율 (%)',
                                                yaxis_title='',
                                                margin=dict(l=100, r=50, t=50, b=50),
                                                xaxis=dict(range=[0, 100]),
                                                hovermode='y unified'
                                            )
                                            st.plotly_chart(fig, width='stretch', key=f'tab2_goal_{idx}')

                                    # ===== 아래: 영양정보 메트릭 =====
                                    st.markdown('영양 정보')
                                    col_cal, col_carb, col_protein, col_fat = st.columns(4)
                                    with col_cal:
                                        st.metric(
                                            '칼로리',
                                            f'{actual_cal:.0f} kcal',
                                            f'{diff:+.0f} kcal',        # ← +/- 기호 명시
                                            delta_color='inverse'        # ← 색상 반전 (초과=빨강, 미달=초록)
                                        )
                                        st.markdown(f'목표 {target_calorie:.0f} kcal')
                                    with col_carb:
                                        st.metric('탄수화물', f'{actual_carb:.1f} g')
                                    with col_protein:
                                        st.metric('단백질', f'{actual_protein:.1f} g')
                                    with col_fat:
                                        st.metric('지방', f'{actual_fat:.1f} g')

                                    # 2개일 때 중간 구분선
                                    if len(results) > 1 and idx == 0:
                                        st.divider()
                                    st.divider()

                    finally:
                        conn.close()
        else:
            with tab2_placeholder.container():
                st.info('👈왼쪽 사이드바에서 정보를 입력해주세요!')
    with tab3:
        #교직원식당
        rest_tab1, rest_tab2, rest_tab3, rest_tab4, rest_tab5 = st.tabs([
            '교직원식당', '중앙식당 1식당','중앙식당 2식당','교육문화1층식당','학생생활관(아람관)'
        ])
        restaurants = [
            ('교직원식당', rest_tab1),
            ('중앙식당 1식당', rest_tab2),
            ('중앙식당 2식당', rest_tab3),
            ('교육문화1층식당', rest_tab4),
            ('학생생활관(아람관)', rest_tab5)
        ]

        for rest_name, tab in restaurants:
            with tab:
                courses = get_restaurant_courses(rest_name)

                if not courses:
                    st.info(f'오늘 {rest_name}의 메뉴 정보가 없습니다.')
                else:
                    st.markdown(f'### {rest_name}')

                    for idx, course in enumerate(courses):
                        with st.container(border=True):
                            st.markdown(f" {course['course']}")
                            col_menu, col_nutrition =st.columns([1.2, 1])
                            with col_menu:
                                st.markdown('상세메뉴')
                                menu_items = get_menu_items(course['course_id'])
                                if menu_items:
                                    for item in menu_items:
                                        st.markdown(f"- {item['menu_name']}")
                                else:
                                    st.caption('세부 메뉴 정보가 없습니다.')
                            with col_nutrition:
                                carb_kcal = course['total_calorie']*4
                                protein_kcal = course['total_protein']*4
                                fat_kcal = course['total_fat']*9

                                fig = go.Figure(data=[
                                    go.Bar(
                                        x=['탄수화물', '단백질', '지방'],
                                        y=[course['total_carb'], course['total_protein'], course['total_fat']],
                                        marker=dict(
                                            color=['#FF6B6B', '#FFABAB','#FF8C8C'],
                                            line=dict(color='rgba(0,0,0,0)', width=0)
                                        ),
                                        text=[f"{course['total_carb']:.1f}g",
                                              f"{course['total_protein']:.1f}g",
                                              f"{course['total_fat']:.1f}g"],
                                        textposition='outside',
                                        hovertemplate='<b>%{x}</b><br>%{y:.1f}g<extra></extra>',
                                        width=0.55
                                    )
                                ])
                                
                                fig.update_layout(
                                    height=280,
                                    showlegend=False,
                                    yaxis_title='함량 (g)',
                                    xaxis_title='',
                                    margin=dict(l=50, r=50, t=30, b=50),
                                    template='plotly_white',  # ← 현대적 하얀 테마
                                    font=dict(family='Arial, sans-serif', size=12),
                                    hovermode='x unified'
                                )
                                
                                st.plotly_chart(fig, width='stretch', key=f'tab3_nutrition_chart{rest_name}_{idx}')
                            
                            st.divider()
                            col_1, col_2, col_3, col_4 = st.columns(4)
                            with col_1:
                                st.metric('칼로리', f"{course['total_calorie']:.0f} kcal")
                            with col_2:
                                st.metric('탄수화물', f"{course['total_carb']:.1f} g")
                            with col_3:
                                st.metric('단백질', f"{course['total_protein']:.1f} g")
                            with col_4:
                                st.metric('지방', f"{course['total_fat']:.1f} g")
                            
                            
                    st.divider()





