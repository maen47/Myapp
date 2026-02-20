import os      # 👈 เพิ่มบรรทัดนี้เข้าไปครับ
import random
import copy
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 1. ฟังก์ชันคำนวณค่าปรับ (Fitness Evaluation) ตามสมการในสมุดจด
def calculate_fitness(chromosome, jobs_data):
    total_cost = 0
    details = []

    for machine, assigned_jobs in chromosome.items():
        current_time = 0
        for job_id in assigned_jobs:
            job = jobs_data[str(job_id)] # ดึงข้อมูลงาน
            p = job['duration']
            d = job['due_date']
            alpha = job['alpha']
            beta = job['beta']

            c = current_time + p
            e = max(0, d - c)
            t = max(0, c - d)
            cost = (alpha * e) + (beta * t)
            total_cost += cost
            
            details.append({
                'Job': job_id, 'Machine': machine, 'Start': current_time,
                'Finish': c, 'Due': d, 'Early': e, 'Late': t, 'Cost': cost
            })
            current_time = c

    return total_cost, details

# 2. ฟังก์ชันหลักของ Genetic Algorithm
def run_genetic_algorithm(jobs_data, num_machines, pop_size=50, generations=100):
    job_ids = list(jobs_data.keys())
    
    # [Initialization] สร้างประชากรเริ่มต้น (สุ่มโยนงานลงเครื่องจักร)
    population = []
    for _ in range(pop_size):
        random.shuffle(job_ids)
        chromo = {f"M{i+1}": [] for i in range(num_machines)}
        for job in job_ids:
            chromo[random.choice(list(chromo.keys()))].append(job)
        population.append(chromo)
        
    best_global_cost = float('inf')
    best_global_chromo = None
    best_global_details = []

    # เริ่มกระบวนการวิวัฒนาการ
    for gen in range(generations):
        scored_population = []
        
        # [Fitness] คำนวณค่าปรับของแต่ละโครโมโซม
        for chromo in population:
            cost, details = calculate_fitness(chromo, jobs_data)
            scored_population.append((cost, chromo, details))
            
            # เก็บตัวที่ดีที่สุดไว้
            if cost < best_global_cost:
                best_global_cost = cost
                best_global_chromo = copy.deepcopy(chromo)
                best_global_details = details

        # เรียงลำดับจากค่าปรับน้อย (ดี) ไปมาก (แย่)
        scored_population.sort(key=lambda x: x[0])
        
        # [Selection & Elitism] เก็บตัวที่เก่งที่สุด 2 ตัวแรกไว้เสมอ (ไม่ให้สูญพันธุ์)
        next_generation = [scored_population[0][1], scored_population[1][1]]
        
        # [Mutation] สร้างลูกหลานตัวใหม่จนครบจำนวนประชากร
        while len(next_generation) < pop_size:
            # เลือกพ่อแม่จากกลุ่มครึ่งบนที่ทำคะแนนได้ดี (คัดสายพันธุ์)
            parent = random.choice(scored_population[:pop_size//2])[1]
            child = copy.deepcopy(parent)
            
            # สุ่มย้ายงาน 1 ชิ้น ไปเสียบเครื่องจักรอื่น (Mutation)
            m1, m2 = random.sample(list(child.keys()), 2)
            if child[m1]:
                job_to_move = random.choice(child[m1])
                child[m1].remove(job_to_move)
                insert_pos = random.randint(0, len(child[m2]))
                child[m2].insert(insert_pos, job_to_move)
            
            next_generation.append(child)
            
        population = next_generation # อัปเดตประชากรในรุ่นถัดไป
        
    return best_global_cost, best_global_chromo, best_global_details

# 3. API รอรับคำสั่งจาก Flutter
@app.route('/api/solve_ga', methods=['POST'])
def solve_ga_api():
    try:
        data = request.get_json()
        jobs_data = data.get('jobs_data')
        num_machines = data.get('num_machines', 2) # ถ้าไม่ส่งมาให้ค่าเริ่มต้นคือ 2 เครื่อง
        
        # สั่งให้ GA ทำงาน (หาจุดที่ดีที่สุด)
        best_cost, best_chromo, best_details = run_genetic_algorithm(jobs_data, num_machines)
        
        return jsonify({
            "status": "success",
            "best_chromosome": best_chromo,
            "total_penalty": best_cost,
            "details": best_details
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    # ให้ใช้ Port จาก Render (ถ้ามี) ถ้าไม่มีค่อยใช้ 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)