from flask import Flask, jsonify
import os
import threading
import websocket
import json
import time
from collections import defaultdict, deque
import math

# ================= CẤU HÌNH =================
WS_URL = "wss://taixiumd5.system32-cloudfare-356783752985678522.monster/signalr/reconnect"
PING_INTERVAL = 15

# ================= BIẾN TOÀN CỤC =================
latest_result = {
    "Phien": None,
    "Xuc_xac_1": -1,
    "Xuc_xac_2": -1,
    "Xuc_xac_3": -1,
    "Tong": -1,
    "Ket_qua": None,
    "Du_doan": "Chờ dữ liệu...",
    "Do_tin_cay": 0,
    "id": "daubuoi"
}

history = deque(maxlen=200)
lock = threading.Lock()

# ================= 20 THUẬT TOÁN TÀI XỈU =================
class TaiXiuReal20Algorithms:
    """20 thuật toán thật - không random - không mô phỏng"""
    
    # === 1. THUẬT TOÁN CÂN BẰNG CHUỖI ===
    @staticmethod
    def algo_01_sequence_balance(history):
        """Cân bằng chuỗi dài/ngắn"""
        if len(history) < 5: return 'T', 0.52
        
        # Phân tích độ dài chuỗi hiện tại
        current = history[-1]
        streak_len = 1
        for i in range(2, min(8, len(history)) + 1):
            if history[-i] == current:
                streak_len += 1
            else:
                break
        
        # Quy tắc: chuỗi dài -> đảo, chuỗi ngắn -> tiếp tục
        if streak_len >= 4:
            return ('X' if current == 'T' else 'T', 0.72)
        elif streak_len == 3:
            return ('X' if current == 'T' else 'T', 0.65)
        elif streak_len == 2:
            return current, 0.60  # Tiếp tục chuỗi ngắn
        else:
            # Đang xen kẽ -> đảo chiều
            return ('X' if current == 'T' else 'T', 0.58)
    
    # === 2. THUẬT TOÁN MA TRẬN CHUYỂN TIẾP ===
    @staticmethod
    def algo_02_transition_matrix(history):
        """Ma trận chuyển tiếp Markov bậc 2"""
        if len(history) < 10: return 'T', 0.53
        
        # Tạo ma trận chuyển tiếp TT->?, TX->?, XT->?, XX->?
        matrix = defaultdict(lambda: {'T': 0, 'X': 0})
        
        for i in range(len(history) - 2):
            state = ''.join(history[i:i+2])
            next_val = history[i+2]
            matrix[state][next_val] += 1
        
        current_state = ''.join(history[-2:])
        
        if current_state in matrix:
            counts = matrix[current_state]
            total = counts['T'] + counts['X']
            
            if total >= 3:
                if counts['T'] > counts['X']:
                    confidence = 0.65 + min(0.10, (counts['T']/total - 0.5) * 2)
                    return 'T', confidence
                else:
                    confidence = 0.65 + min(0.10, (counts['X']/total - 0.5) * 2)
                    return 'X', confidence
        
        return 'T' if current_state[0] == 'X' else 'X', 0.57
    
    # === 3. THUẬT TOÁN PHÂN TÍCH TẦN SUẤT ===
    @staticmethod
    def algo_03_frequency_analysis(history):
        """Phân tích tần suất xuất hiện"""
        if len(history) < 15: return 'T', 0.53
        
        tai_count = history.count('T')
        xiu_count = len(history) - tai_count
        
        # Lý thuyết xác suất thật: T=104/216≈0.4815, X=112/216≈0.5185
        if tai_count > xiu_count + 5:  # Tài nhiều hơn Xỉu 5 lần
            return 'X', 0.70 + min(0.05, (tai_count - xiu_count - 5) * 0.01)
        elif xiu_count > tai_count + 5:  # Xỉu nhiều hơn Tài 5 lần
            return 'T', 0.70 + min(0.05, (xiu_count - tai_count - 5) * 0.01)
        
        # Tần suất cân bằng -> dựa vào xu hướng gần nhất
        last_5 = history[-5:] if len(history) >= 5 else history
        if last_5.count('T') > last_5.count('X'):
            return 'T', 0.58
        else:
            return 'X', 0.58
    
    # === 4. THUẬT TOÁN PATTERN NHỊ PHÂN ===
    @staticmethod
    def algo_04_binary_pattern(history):
        """Phát hiện pattern trong chuỗi nhị phân"""
        if len(history) < 8: return 'T', 0.52
        
        binary = ''.join(['1' if h == 'T' else '0' for h in history])
        
        # Kiểm tra pattern đặc biệt
        patterns = {
            '101': ('0', 0.68),  # T X T -> X
            '010': ('1', 0.68),  # X T X -> T
            '110': ('0', 0.65),  # T T X -> X
            '001': ('1', 0.65),  # X X T -> T
            '100': ('1', 0.63),  # T X X -> T
            '011': ('0', 0.63),  # X T T -> X
        }
        
        for pattern, (next_bit, conf) in patterns.items():
            if binary.endswith(pattern):
                return ('T' if next_bit == '1' else 'X', conf)
        
        # Phân tích tỉ lệ 1/0 trong 10 bit gần nhất
        if len(binary) >= 10:
            recent = binary[-10:]
            ones = recent.count('1')
            if ones >= 7:
                return 'X', 0.67  # Nhiều 1 (Tài) quá -> Xỉu
            elif ones <= 3:
                return 'T', 0.67  # Ít 1 (Tài) quá -> Tài
        
        return 'T' if binary[-1] == '0' else 'X', 0.56
    
    # === 5. THUẬT TOÁN ĐỘNG LƯỢNG ===
    @staticmethod
    def algo_05_momentum(history):
        """Phân tích động lượng xu hướng"""
        if len(history) < 8: return 'T', 0.52
        
        # Tính momentum 6 phiên gần nhất
        momentum = 0
        for i in range(1, min(7, len(history))):
            momentum += 1 if history[-i] == 'T' else -1
        
        if momentum >= 4:  # Tài mạnh
            return 'X', 0.68
        elif momentum <= -4:  # Xỉu mạnh
            return 'T', 0.68
        elif momentum >= 2:
            return 'T', 0.62
        elif momentum <= -2:
            return 'X', 0.62
        
        return history[-1], 0.56
    
    # === 6. THUẬT TOÁN PHÂN TÍCH CỤM ===
    @staticmethod
    def algo_06_cluster_analysis(history):
        """Phân tích cụm xuất hiện"""
        if len(history) < 12: return 'T', 0.53
        
        # Tìm các cụm Tài/Xỉu
        clusters = []
        current = {'value': history[0], 'count': 1}
        
        for i in range(1, len(history)):
            if history[i] == current['value']:
                current['count'] += 1
            else:
                clusters.append(current.copy())
                current = {'value': history[i], 'count': 1}
        clusters.append(current)
        
        # Phân tích cụm hiện tại
        current_cluster = clusters[-1]
        
        if len(clusters) >= 3:
            prev_clusters = clusters[-3:-1]
            avg_len = sum(c['count'] for c in prev_clusters) / 2
            
            if current_cluster['count'] > avg_len * 1.3:
                # Cụm dài bất thường -> sắp kết thúc
                return ('X' if current_cluster['value'] == 'T' else 'T', 0.70)
            elif current_cluster['count'] < avg_len * 0.7:
                # Cụm ngắn -> có thể kéo dài
                return current_cluster['value'], 0.65
        
        return 'T' if len(history) % 3 == 0 else 'X', 0.57
    
    # === 7. THUẬT TOÁN GAP PHÂN TÍCH ===
    @staticmethod
    def algo_07_gap_analysis(history):
        """Phân tích khoảng cách xuất hiện"""
        if len(history) < 10: return 'T', 0.53
        
        # Tìm vị trí xuất hiện cuối cùng của T và X
        t_positions = [i for i, val in enumerate(history) if val == 'T']
        x_positions = [i for i, val in enumerate(history) if val == 'X']
        
        if len(t_positions) >= 2 and len(x_positions) >= 2:
            # Tính khoảng cách trung bình
            t_gaps = [t_positions[i] - t_positions[i-1] for i in range(1, len(t_positions))]
            x_gaps = [x_positions[i] - x_positions[i-1] for i in range(1, len(x_positions))]
            
            avg_t_gap = sum(t_gaps) / len(t_gaps) if t_gaps else 0
            avg_x_gap = sum(x_gaps) / len(x_gaps) if x_gaps else 0
            
            last_t = t_positions[-1] if t_positions else 0
            last_x = x_positions[-1] if x_positions else 0
            
            # Dự đoán dựa trên khoảng cách
            if avg_t_gap > 0 and (len(history) - last_t) > avg_t_gap * 0.7:
                return 'T', 0.68
            if avg_x_gap > 0 and (len(history) - last_x) > avg_x_gap * 0.7:
                return 'X', 0.68
        
        return history[-1], 0.56
    
    # === 8. THUẬT TOÁN CHU KỲ ===
    @staticmethod
    def algo_08_cycle_detection(history):
        """Phát hiện chu kỳ lặp"""
        if len(history) < 12: return 'T', 0.53
        
        # Tìm chu kỳ độ dài 2-4
        for cycle_len in range(2, 5):
            if len(history) >= cycle_len * 3:
                cycle1 = history[-cycle_len*3:-cycle_len*2]
                cycle2 = history[-cycle_len*2:-cycle_len]
                cycle3 = history[-cycle_len:]
                
                if cycle1 == cycle2 == cycle3:
                    # Tìm thấy chu kỳ
                    return cycle1[0], 0.75
        
        # Kiểm tra pattern ABAB
        if len(history) >= 8:
            last_8 = history[-8:]
            if (last_8[0] == last_8[2] == last_8[4] == last_8[6] and
                last_8[1] == last_8[3] == last_8[5] == last_8[7]):
                return last_8[0], 0.70
        
        return 'T' if len(history) % 4 == 0 else 'X', 0.57
    
    # === 9. THUẬT TOÁN TÍN HIỆU ĐẢO CHIỀU ===
    @staticmethod
    def algo_09_reversal_signal(history):
        """Phát hiện điểm đảo chiều"""
        if len(history) < 8: return 'T', 0.52
        
        # Tìm các điểm thay đổi
        change_points = []
        for i in range(1, len(history)):
            if history[i] != history[i-1]:
                change_points.append(i)
        
        if len(change_points) >= 3:
            # Tính chu kỳ đảo chiều
            intervals = [change_points[i] - change_points[i-1] for i in range(1, len(change_points))]
            avg_interval = sum(intervals) / len(intervals)
            
            last_change = change_points[-1]
            current_pos = len(history)
            
            # Dự đoán đảo chiều sắp tới
            if (current_pos - last_change) > avg_interval * 0.6:
                return ('X' if history[-1] == 'T' else 'T', 0.68)
        
        return history[-1], 0.56
    
    # === 10. THUẬT TOÁN XÁC SUẤT CÓ ĐIỀU KIỆN ===
    @staticmethod
    def algo_10_conditional_probability(history):
        """Xác suất có điều kiện"""
        if len(history) < 12: return 'T', 0.53
        
        # Tính P(T|...) và P(X|...)
        t_given_t = 0
        t_given_x = 0
        x_given_t = 0
        x_given_x = 0
        
        for i in range(len(history) - 1):
            if history[i] == 'T':
                if history[i+1] == 'T':
                    t_given_t += 1
                else:
                    x_given_t += 1
            else:
                if history[i+1] == 'T':
                    t_given_x += 1
                else:
                    x_given_x += 1
        
        total_t = t_given_t + x_given_t
        total_x = t_given_x + x_given_x
        
        if total_t > 3 and total_x > 3:
            p_t_given_t = t_given_t / total_t
            p_x_given_t = x_given_t / total_t
            p_t_given_x = t_given_x / total_x
            p_x_given_x = x_given_x / total_x
            
            last = history[-1]
            
            if last == 'T':
                if p_x_given_t > p_t_given_t:
                    return 'X', p_x_given_t + 0.5
                else:
                    return 'T', p_t_given_t + 0.5
            else:
                if p_t_given_x > p_x_given_x:
                    return 'T', p_t_given_x + 0.5
                else:
                    return 'X', p_x_given_x + 0.5
        
        return 'T' if len(history) % 2 == 0 else 'X', 0.55
    
    # === 11. THUẬT TOÁN TRUNG BÌNH ĐỘNG ===
    @staticmethod
    def algo_11_moving_average(history):
        """Phân tích bằng trung bình động"""
        if len(history) < 10: return 'T', 0.53
        
        values = [1 if h == 'T' else 0 for h in history]
        
        # Tính MA5 và MA10
        ma5 = sum(values[-5:]) / 5 if len(values) >= 5 else 0.5
        ma10 = sum(values[-10:]) / 10 if len(values) >= 10 else 0.5
        
        if ma5 > ma10 + 0.2:
            return 'T', 0.68
        elif ma5 < ma10 - 0.2:
            return 'X', 0.68
        elif ma5 > ma10:
            return 'T', 0.62
        else:
            return 'X', 0.62
    
    # === 12. THUẬT TOÁN BIẾN ĐỘNG ===
    @staticmethod
    def algo_12_volatility(history):
        """Phân tích biến động"""
        if len(history) < 12: return 'T', 0.53
        
        # Tính tỉ lệ thay đổi
        changes = 0
        for i in range(1, min(11, len(history))):
            if history[-i] != history[-(i+1)]:
                changes += 1
        
        volatility = changes / 10
        
        if volatility > 0.7:  # Biến động cao
            return ('X' if history[-1] == 'T' else 'T', 0.66)
        elif volatility < 0.3:  # Biến động thấp
            return history[-1], 0.68
        else:
            return 'T' if len(history) % 3 == 0 else 'X', 0.58
    
    # === 13. THUẬT TOÁN ENTROPY ===
    @staticmethod
    def algo_13_entropy_analysis(history):
        """Phân tích entropy"""
        if len(history) < 10: return 'T', 0.52
        
        t_count = history.count('T')
        p_t = t_count / len(history)
        p_x = 1 - p_t
        
        entropy = 0
        if p_t > 0:
            entropy -= p_t * math.log2(p_t)
        if p_x > 0:
            entropy -= p_x * math.log2(p_x)
        
        # Entropy cao -> random, entropy thấp -> có pattern
        if entropy < 0.5:  # Có pattern
            return history[-1], 0.65
        elif entropy > 0.95:  # Rất random
            return ('X' if history[-1] == 'T' else 'T', 0.62)
        else:
            return 'T' if p_t > p_x else 'X', 0.58
    
    # === 14. THUẬT TOÁN PATTERN NGẮN ===
    @staticmethod
    def algo_14_short_pattern(history):
        """Phát hiện pattern ngắn"""
        if len(history) < 6: return 'T', 0.52
        
        last_3 = ''.join(history[-3:])
        
        patterns = {
            'TTT': ('X', 0.72),
            'TTX': ('T', 0.65),
            'TXT': ('X', 0.63),
            'TXX': ('T', 0.65),
            'XTT': ('X', 0.63),
            'XTX': ('T', 0.65),
            'XXT': ('X', 0.65),
            'XXX': ('T', 0.72),
        }
        
        if last_3 in patterns:
            next_val, conf = patterns[last_3]
            
            # Kiểm tra xác suất thực tế
            pattern_count = 0
            correct_count = 0
            
            for i in range(len(history) - 3):
                if ''.join(history[i:i+3]) == last_3:
                    pattern_count += 1
                    if history[i+3] == next_val:
                        correct_count += 1
            
            if pattern_count >= 2:
                actual_conf = correct_count / pattern_count
                return next_val, max(conf, actual_conf * 0.8 + 0.2)
        
        return 'T' if last_3[1] == 'X' else 'X', 0.57
    
    # === 15. THUẬT TOÁN PHÂN TÍCH DÃY ===
    @staticmethod
    def algo_15_sequence_analysis(history):
        """Phân tích dãy số liên tiếp"""
        if len(history) < 8: return 'T', 0.52
        
        # Tìm dãy con phổ biến độ dài 2
        pairs = defaultdict(int)
        for i in range(len(history) - 1):
            pair = ''.join(history[i:i+2])
            pairs[pair] += 1
        
        if pairs:
            max_pair = max(pairs.items(), key=lambda x: x[1])
            if max_pair[1] >= 3:
                return max_pair[0][0], 0.68
        
        return 'T' if history[-1] == 'X' else 'X', 0.56
    
    # === 16. THUẬT TOÁN Z-SCORE ===
    @staticmethod
    def algo_16_zscore(history):
        """Phân tích Z-Score"""
        if len(history) < 8: return 'T', 0.53
        
        values = [1 if h == 'T' else 0 for h in history[-8:]]
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(variance) if variance > 0 else 0.001
        
        z_score = (values[-1] - mean) / std if std > 0 else 0
        
        if abs(z_score) > 1.5:
            return ('X' if values[-1] == 1 else 'T', 0.70)
        elif z_score > 0:
            return 'T', 0.60
        else:
            return 'X', 0.60
    
    # === 17. THUẬT TOÁN TƯƠNG QUAN ===
    @staticmethod
    def algo_17_correlation(history):
        """Phân tích tương quan"""
        if len(history) < 10: return 'T', 0.53
        
        values = [1 if h == 'T' else 0 for h in history]
        
        # Tính tương quan lag 1
        if len(values) > 1:
            x = values[:-1]
            y = values[1:]
            
            # Tính covariance
            mean_x = sum(x) / len(x)
            mean_y = sum(y) / len(y)
            
            covariance = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x))) / len(x)
            std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / len(x))
            std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / len(y))
            
            correlation = covariance / (std_x * std_y) if std_x > 0 and std_y > 0 else 0
            
            if correlation > 0.3:
                return history[-1], 0.65
            elif correlation < -0.3:
                return ('X' if history[-1] == 'T' else 'T', 0.65)
        
        return 'T' if len(history) % 3 == 0 else 'X', 0.56
    
    # === 18. THUẬT TOÁN MẬT ĐỘ ===
    @staticmethod
    def algo_18_density(history):
        """Phân tích mật độ xuất hiện"""
        if len(history) < 12: return 'T', 0.53
        
        window = min(10, len(history))
        recent = history[-window:]
        tai_density = recent.count('T') / window
        
        if tai_density > 0.7:
            return 'X', 0.68
        elif tai_density < 0.3:
            return 'T', 0.68
        elif tai_density > 0.5:
            return 'T', 0.62
        else:
            return 'X', 0.62
    
    # === 19. THUẬT TOÁN THỐNG KÊ ===
    @staticmethod
    def algo_19_statistical(history):
        """Phân tích thống kê nâng cao"""
        if len(history) < 15: return 'T', 0.54
        
        # Tính các chỉ số thống kê
        values = [1 if h == 'T' else 0 for h in history]
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        # Phân tích xu hướng
        recent_mean = sum(values[-5:]) / 5 if len(values) >= 5 else mean
        
        if recent_mean > mean + 0.3:
            return 'X', 0.70
        elif recent_mean < mean - 0.3:
            return 'T', 0.70
        elif recent_mean > mean:
            return 'T', 0.62
        else:
            return 'X', 0.62
    
    # === 20. THUẬT TOÁN TỔNG HỢP THÔNG MINH ===
    @staticmethod
    def algo_20_smart_ensemble(history):
        """Tổng hợp thông minh từ các thuật toán"""
        if len(history) < 8: return 'T', 0.52
        
        # Chọn 5 thuật toán tốt nhất
        methods = [
            TaiXiuReal20Algorithms.algo_01_sequence_balance,
            TaiXiuReal20Algorithms.algo_02_transition_matrix,
            TaiXiuReal20Algorithms.algo_05_momentum,
            TaiXiuReal20Algorithms.algo_09_reversal_signal,
            TaiXiuReal20Algorithms.algo_14_short_pattern,
        ]
        
        predictions = []
        confidences = []
        
        for method in methods:
            try:
                pred, conf = method(history)
                predictions.append(pred)
                confidences.append(conf)
            except:
                continue
        
        if not predictions:
            return 'T', 0.50
        
        # Weighted voting
        t_score = sum(conf for pred, conf in zip(predictions, confidences) if pred == 'T')
        x_score = sum(conf for pred, conf in zip(predictions, confidences) if pred == 'X')
        
        if t_score > x_score:
            final_conf = (t_score / (t_score + x_score)) * 0.7 + 0.3
            return 'T', min(0.75, final_conf)
        else:
            final_conf = (x_score / (t_score + x_score)) * 0.7 + 0.3
            return 'X', min(0.75, final_conf)

# ================= HÀM DỰ ĐOÁN =================
def predict_next():
    """Dự đoán kết quả tiếp theo"""
    history_list = list(history)
    
    if len(history_list) < 5:
        return "Chờ dữ liệu...", 0.0
    
    try:
        prediction, confidence = TaiXiuReal20Algorithms.algo_20_smart_ensemble(history_list)
        ket_qua = "Tài" if prediction == 'T' else "Xỉu"
        confidence_percent = min(100, max(0, confidence * 100))
        return ket_qua, round(confidence_percent, 1)
    
    except Exception as e:
        print(f"❌ Lỗi dự đoán: {e}")
        return "Lỗi dự đoán", 0.0

# ================= HÀM TÀI / XỈU =================
def get_tai_xiu(d1, d2, d3):
    return "Tài" if (d1 + d2 + d3) >= 11 else "Xỉu"

# ================= WEBSOCKET =================
def on_message(ws, message):
    global latest_result
    try:
        data = json.loads(message)

        if isinstance(data, dict) and "M" in data:
            for item in data["M"]:
                if item.get("M") == "Md5sessionInfo":
                    info = item["A"][0]
                    session_id = info.get("SessionID")
                    result = info.get("Result", {})

                    d1 = result.get("Dice1", -1)
                    d2 = result.get("Dice2", -1)
                    d3 = result.get("Dice3", -1)

                    if d1 != -1 and d2 != -1 and d3 != -1:
                        with lock:
                            if latest_result["Phien"] != session_id:
                                total = d1 + d2 + d3
                                ket_qua = get_tai_xiu(d1, d2, d3)

                                # Lưu vào lịch sử
                                history.append("T" if ket_qua == "Tài" else "X")

                                # Dự đoán kết quả tiếp theo
                                du_doan, do_tin_cay = predict_next()

                                latest_result.update({
                                    "Phien": session_id,
                                    "Xuc_xac_1": d1,
                                    "Xuc_xac_2": d2,
                                    "Xuc_xac_3": d3,
                                    "Tong": total,
                                    "Ket_qua": ket_qua,
                                    "Du_doan": du_doan,
                                    "Do_tin_cay": do_tin_cay
                                })

                                print(f"✅ Phiên {session_id} | {ket_qua} | {d1}-{d2}-{d3} | Dự đoán: {du_doan} ({do_tin_cay}%)")
                                print(f"   Lịch sử ({len(history)}): {''.join(list(history)[-10:])}")

    except Exception as e:
        print("❌ WS message error:", e)

def on_error(ws, error):
    print("❌ WS error:", error)

def on_close(ws, code, msg):
    print("🔄 WS đóng – reconnect sau 3s")
    time.sleep(3)
    start_ws_thread()

def on_open(ws):
    def ping_loop():
        while True:
            try:
                ws.send(json.dumps({
                    "M": "PingPong",
                    "H": "md5luckydiceHub",
                    "I": 0
                }))
                time.sleep(PING_INTERVAL)
            except:
                break
    threading.Thread(target=ping_loop, daemon=True).start()

def start_ws_thread():
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=10, ping_timeout=5)

# ================= FLASK API =================
app = Flask(__name__)

# 🔥 KEEP ALIVE – CHỐNG NGỦ ĐÔNG
@app.route("/ping")
def ping():
    return "pong"

@app.route("/api/taixiumd5")
def api_taixiu():
    with lock:
        return jsonify(latest_result)

@app.route("/api/history")
def api_history():
    with lock:
        return jsonify({
            "total": len(history),
            "history": list(history)
        })

# ================= MAIN =================
if __name__ == "__main__":
    threading.Thread(
        target=start_ws_thread,
        daemon=True
    ).start()

    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 RUNNING ON PORT {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
