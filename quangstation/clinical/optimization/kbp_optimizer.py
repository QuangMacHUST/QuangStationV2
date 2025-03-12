#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module tối ưu hóa dựa trên kiến thức (Knowledge-Based Planning - KBP)
cho hệ thống lập kế hoạch xạ trị QuangStation V2.

Mô-đun này sử dụng dữ liệu từ các kế hoạch xạ trị trước đó để dự đoán
các ràng buộc tối ưu cho các cấu trúc mới.
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import pickle
import json
import logging
from scipy.spatial.distance import cdist
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

from quangstation.core.utils.logging import get_logger
from quangstation.core.utils.config import get_config
from quangstation.clinical.data_management.patient_db import PatientDatabase
from quangstation.clinical.optimization.goal_optimizer import OptimizationGoal

logger = get_logger(__name__)

class KnowledgeBasedPlanningOptimizer:
    """
    Lớp tối ưu hóa dựa trên kiến thức (KBP) sử dụng mô hình học máy
    để dự đoán các ràng buộc tối ưu cho kế hoạch xạ trị dựa trên dữ liệu lịch sử.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Khởi tạo KBP Optimizer.
        
        Args:
            model_path: Đường dẫn đến mô hình đã huấn luyện (nếu có)
        """
        self.logger = get_logger("KBP_Optimizer")
        self.config = get_config()
        self.model_path = model_path
        self.models = {}  # Mô hình cho từng loại cơ quan
        self.scalers = {}  # Scalers cho từng loại cơ quan
        self.available_models = []  # Danh sách các mô hình có sẵn
        self.feature_columns = []  # Các cột đặc trưng sử dụng trong mô hình
        self.target_columns = []  # Các cột mục tiêu để dự đoán
        self.db = PatientDatabase()
        
        # Thiết lập đường dẫn lưu mô hình mặc định
        if not model_path:
            self.model_path = get_config("optimization.kbp_models_dir", 
                               os.path.join(get_config("workspace.root_dir"), "models", "kbp"))
            os.makedirs(self.model_path, exist_ok=True)
        
        # Tải danh sách mô hình có sẵn
        self._load_available_models()
        
    def _load_available_models(self):
        """Tải danh sách các mô hình KBP có sẵn."""
        try:
            if not os.path.exists(self.model_path):
                self.logger.warning(f"Thư mục mô hình không tồn tại: {self.model_path}")
                return
            
            model_files = [f for f in os.listdir(self.model_path) if f.endswith('.pkl')]
            self.available_models = [os.path.splitext(f)[0] for f in model_files]
            
            # Tải thông tin mô hình từ tệp json nếu có
            info_path = os.path.join(self.model_path, "model_info.json")
            if os.path.exists(info_path):
                with open(info_path, 'r') as f:
                    model_info = json.load(f)
                    if 'feature_columns' in model_info:
                        self.feature_columns = model_info['feature_columns']
                    if 'target_columns' in model_info:
                        self.target_columns = model_info['target_columns']
            
            self.logger.info(f"Đã tìm thấy {len(self.available_models)} mô hình KBP: {', '.join(self.available_models)}")
        except Exception as e:
            self.logger.error(f"Lỗi khi tải danh sách mô hình: {str(e)}")
            
    def load_model(self, organ_name: str) -> bool:
        """
        Tải mô hình KBP cho một cơ quan cụ thể.
        
        Args:
            organ_name: Tên cơ quan (ví dụ: parotid_left, parotid_right, spinal_cord)
            
        Returns:
            bool: True nếu tải thành công, False nếu không
        """
        try:
            # Chuẩn hóa tên cơ quan
            organ_name = organ_name.lower().replace(" ", "_")
            
            # Kiểm tra xem mô hình đã được tải chưa
            if organ_name in self.models:
                self.logger.info(f"Mô hình cho {organ_name} đã được tải trước đó")
                return True
            
            # Tìm file mô hình
            model_file = os.path.join(self.model_path, f"{organ_name}_model.pkl")
            
            if os.path.exists(model_file):
                with open(model_file, 'rb') as f:
                    self.models[organ_name] = pickle.load(f)
                self.logger.info(f"Đã tải mô hình cho {organ_name}")
                return True
            else:
                # Tìm mô hình tương tự
                similar_model = self._find_similar_model(organ_name)
                if similar_model:
                    self.logger.info(f"Sử dụng mô hình {similar_model} cho {organ_name}")
                    with open(os.path.join(self.model_path, f"{similar_model}_model.pkl"), 'rb') as f:
                        self.models[organ_name] = pickle.load(f)
                    return True
                else:
                    self.logger.warning(f"Không tìm thấy mô hình cho {organ_name}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Lỗi khi tải mô hình {organ_name}: {str(e)}")
            return False
    
    def extract_features(self, structures: Dict[str, Any], plan_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Trích xuất đặc trưng từ dữ liệu cấu trúc và kế hoạch.
        
        Args:
            structures: Dictionary chứa dữ liệu cấu trúc
            plan_data: Dictionary chứa dữ liệu kế hoạch
            
        Returns:
            DataFrame chứa các đặc trưng đã trích xuất
        """
        features = {}
        
        try:
            # Tìm cấu trúc PTV chính
            ptv_name = None
            for name in structures.keys():
                if name.startswith('PTV'):
                    ptv_name = name
                    break
            
            if not ptv_name:
                self.logger.warning("Không tìm thấy cấu trúc PTV")
                return pd.DataFrame()
            
            ptv_mask = structures[ptv_name]
            ptv_volume = np.sum(ptv_mask) * 0.001  # Tính thể tích (cc)
            
            # Các đặc trưng cơ bản
            features['ptv_volume'] = ptv_volume
            features['total_dose'] = plan_data.get('total_dose', 0)
            features['fractions'] = plan_data.get('fraction_count', 0)
            features['technique'] = plan_data.get('technique', 'VMAT')
            
            # Tính đặc trưng hình học cho từng cơ quan
            for organ_name, organ_mask in structures.items():
                if organ_name.startswith('PTV') or organ_name.startswith('CTV') or organ_name.startswith('GTV'):
                    continue
                
                # Tính thể tích
                organ_volume = np.sum(organ_mask) * 0.001  # cc
                features[f"{organ_name}_volume"] = organ_volume
                
                # Tính khoảng cách gần nhất đến PTV
                overlap = np.logical_and(ptv_mask, organ_mask)
                overlap_volume = np.sum(overlap) * 0.001  # cc
                features[f"{organ_name}_ptv_overlap"] = overlap_volume
                
                # Tính phần trăm thể tích chồng lấp
                if organ_volume > 0:
                    features[f"{organ_name}_ptv_overlap_percent"] = (overlap_volume / organ_volume) * 100
                else:
                    features[f"{organ_name}_ptv_overlap_percent"] = 0
                
                # Tính khoảng cách từ trọng tâm cơ quan đến trọng tâm PTV
                if np.sum(ptv_mask) > 0 and np.sum(organ_mask) > 0:
                    ptv_indices = np.argwhere(ptv_mask)
                    organ_indices = np.argwhere(organ_mask)
                    
                    ptv_centroid = np.mean(ptv_indices, axis=0)
                    organ_centroid = np.mean(organ_indices, axis=0)
                    
                    distance = np.linalg.norm(ptv_centroid - organ_centroid)
                    features[f"{organ_name}_distance_to_ptv"] = distance
                else:
                    features[f"{organ_name}_distance_to_ptv"] = -1
            
            return pd.DataFrame([features])
            
        except Exception as e:
            self.logger.error(f"Lỗi khi trích xuất đặc trưng: {str(e)}")
            return pd.DataFrame()
    
    def predict_dose_metrics(self, features: pd.DataFrame, organ_name: str) -> Dict[str, float]:
        """
        Dự đoán các chỉ số liều cho một cơ quan dựa trên các đặc trưng.
        
        Args:
            features: DataFrame chứa các đặc trưng
            organ_name: Tên cơ quan cần dự đoán
            
        Returns:
            Dictionary chứa các chỉ số liều dự đoán
        """
        result = {}
        
        try:
            # Kiểm tra xem có mô hình cho cơ quan này không
            if organ_name not in self.models:
                if not self.load_model(organ_name):
                    # Tìm kiếm mô hình tương tự nếu không có mô hình chính xác
                    similar_model = self._find_similar_model(organ_name)
                    if not similar_model or not self.load_model(similar_model):
                        self.logger.warning(f"Không có mô hình cho {organ_name}")
                        return result
            
            # Chuẩn bị đặc trưng đầu vào
            X = features[self.feature_columns].fillna(0)
            
            # Chuẩn hóa dữ liệu
            X_scaled = self.scalers[organ_name].transform(X)
            
            # Dự đoán
            y_pred = self.models[organ_name].predict(X_scaled)
            
            # Chuyển đổi kết quả dự đoán thành dictionary
            for i, col in enumerate(self.target_columns):
                result[col] = y_pred[0][i] if isinstance(y_pred[0], np.ndarray) else y_pred[i]
            
            return result
        
        except Exception as e:
            self.logger.error(f"Lỗi khi dự đoán chỉ số liều cho {organ_name}: {str(e)}")
            return result
    
    def _find_similar_model(self, organ_name: str) -> Optional[str]:
        """
        Tìm mô hình tương tự cho một cơ quan nếu không có mô hình chính xác.
        
        Args:
            organ_name: Tên cơ quan cần tìm mô hình tương tự
            
        Returns:
            Optional[str]: Tên mô hình tương tự nếu tìm thấy, None nếu không
        """
        # Chuẩn hóa tên cơ quan
        organ_lower = organ_name.lower()
        
        # Tải danh sách mô hình từ file cấu hình
        model_info_path = os.path.join(self.model_path, "model_info.json")
        if os.path.exists(model_info_path):
            try:
                with open(model_info_path, 'r') as f:
                    model_info = json.load(f)
                if 'models' in model_info:
                    # Tìm kiếm trong danh sách mô hình đã định nghĩa
                    for model_name in model_info['models'].keys():
                        if model_name.lower() in organ_lower or organ_lower in model_name.lower():
                            self.logger.info(f"Tìm thấy mô hình tương tự {model_name} cho {organ_name}")
                            return model_name
            except Exception as e:
                self.logger.error(f"Lỗi khi tải model_info.json: {str(e)}")
        
        # Danh sách từ khóa liên quan (dự phòng nếu không có model_info.json)
        keywords = {
            'parotid': ['parotid', 'tuyến mang tai'],
            'spinal_cord': ['spinal', 'cord', 'tủy sống'],
            'brainstem': ['brain', 'stem', 'thân não'],
            'lung': ['lung', 'phổi'],
            'heart': ['heart', 'tim'],
            'liver': ['liver', 'gan'],
            'kidney': ['kidney', 'thận'],
            'esophagus': ['esophagus', 'thực quản'],
            'larynx': ['larynx', 'thanh quản'],
            'mandible': ['mandible', 'xương hàm'],
            'oral_cavity': ['oral', 'cavity', 'khoang miệng'],
            'eye': ['eye', 'mắt', 'globe'],
            'optic_nerve': ['optic', 'nerve', 'thần kinh thị giác'],
            'chiasm': ['chiasm', 'giao thoa'],
            'rectum': ['rectum', 'trực tràng'],
            'bladder': ['bladder', 'bàng quang'],
            'bowel': ['bowel', 'ruột'],
            'femoral_head': ['femoral', 'head', 'chỏm xương đùi'],
            'thyroid': ['thyroid', 'tuyến giáp']
        }
        
        # Tìm kiếm dựa trên từ khóa
        max_similarity = 0
        best_match = None
        
        # Hàm đánh giá độ tương đồng giữa chuỗi
        def similarity_score(str1, str2):
            from difflib import SequenceMatcher
            return SequenceMatcher(None, str1, str2).ratio()
        
        # Kiểm tra từng từ khóa
        for model_key, related_keywords in keywords.items():
            for keyword in related_keywords:
                if keyword in organ_lower:
                    # Tìm mô hình có sẵn phù hợp với từ khóa
                    for available_model in self.available_models:
                        if model_key in available_model.lower():
                            self.logger.info(f"Tìm thấy mô hình {available_model} cho từ khóa {keyword}")
                            return available_model
        
        # Nếu không tìm thấy từ khóa, so sánh theo độ tương đồng chuỗi
        for available_model in self.available_models:
            score = similarity_score(organ_lower, available_model.lower())
            if score > max_similarity:
                max_similarity = score
                best_match = available_model
        
        # Chỉ trả về kết quả nếu đủ tương đồng (>= 60%)
        if max_similarity >= 0.6:
            self.logger.info(f"Tìm thấy mô hình {best_match} cho {organ_name} với độ tương đồng {max_similarity:.2f}")
            return best_match
            
        self.logger.warning(f"Không tìm thấy mô hình tương tự cho {organ_name}")
        return None
    
    def suggest_optimization_goals(self, structures: Dict[str, Any], plan_data: Dict[str, Any]) -> List[OptimizationGoal]:
        """
        Đề xuất các mục tiêu tối ưu hóa dựa trên dự đoán từ mô hình KBP.
        
        Args:
            structures: Dictionary chứa dữ liệu cấu trúc
            plan_data: Dictionary chứa dữ liệu kế hoạch
            
        Returns:
            Danh sách các mục tiêu tối ưu hóa được đề xuất
        """
        optimization_goals = []
        
        try:
            # Tải thông tin từ model_info.json
            model_constraints = {}
            model_info_path = os.path.join(self.model_path, "model_info.json")
            if os.path.exists(model_info_path):
                try:
                    with open(model_info_path, 'r') as f:
                        model_info = json.load(f)
                    if 'models' in model_info:
                        for model_name, info in model_info['models'].items():
                            if 'constraints' in info:
                                model_constraints[model_name] = info['constraints']
                except Exception as e:
                    self.logger.error(f"Lỗi khi tải model_info.json: {str(e)}")
            
            # Trích xuất đặc trưng
            features = self.extract_features(structures, plan_data)
            if features.empty:
                self.logger.warning("Không thể trích xuất đặc trưng")
                return optimization_goals
            
            # Mặc định ưu tiên cơ quan nếu không có trong model_info
            default_oar_priority = {
                'SpinalCord': 1,
                'Brainstem': 1,
                'OpticChiasm': 1,
                'OpticNerve': 1,
                'ParotidLeft': 2,
                'ParotidRight': 2,
                'Larynx': 2,
                'Mandible': 3,
                'OralCavity': 3,
                'Esophagus': 3,
                'Thyroid': 4,
                'Lips': 4,
                'Heart': 2,
                'Lung': 2,
                'Liver': 3,
                'Kidney': 3,
                'Bladder': 3,
                'Rectum': 3
            }
            
            # Thêm mục tiêu cho PTV (mục tiêu điều trị)
            for struct_name in structures.keys():
                if struct_name.startswith('PTV'):
                    if 'total_dose' in plan_data and plan_data['total_dose']:
                        prescription_dose = float(plan_data['total_dose'])
                        
                        # Mục tiêu liều tối thiểu cho PTV
                        optimization_goals.append(
                            OptimizationGoal(
                                structure_name=struct_name,
                                goal_type=OptimizationGoal.TYPE_MIN_DOSE,
                                dose_value=prescription_dose * 0.95,  # 95% của liều kê toa
                                weight=100.0,
                                priority=1,
                                is_required=True
                            )
                        )
                        
                        # Mục tiêu liều đồng đều cho PTV
                        optimization_goals.append(
                            OptimizationGoal(
                                structure_name=struct_name,
                                goal_type=OptimizationGoal.TYPE_UNIFORM_DOSE,
                                dose_value=prescription_dose,
                                weight=80.0,
                                priority=1,
                                is_required=True
                            )
                        )
                        
                        # Mục tiêu liều tối đa cho PTV
                        optimization_goals.append(
                            OptimizationGoal(
                                structure_name=struct_name,
                                goal_type=OptimizationGoal.TYPE_MAX_DOSE,
                                dose_value=prescription_dose * 1.07,  # 107% của liều kê toa
                                weight=100.0,
                                priority=1,
                                is_required=True
                            )
                        )
                        
                        self.logger.info(f"Đã thêm mục tiêu cho {struct_name} với liều kê toa {prescription_dose} Gy")
            
            # Danh sách cơ quan trong kế hoạch (không bao gồm PTV, CTV, GTV)
            organs = [name for name in structures.keys() 
                      if not (name.startswith('PTV') or name.startswith('CTV') or name.startswith('GTV'))]
            
            for organ in organs:
                # Tìm mô hình tương ứng
                model_name = None
                
                # Tìm khớp chính xác trong model_constraints
                for key in model_constraints.keys():
                    if key.lower() == organ.lower() or key.lower() in organ.lower() or organ.lower() in key.lower():
                        model_name = key
                        break
                
                # Nếu không có khớp chính xác, tìm mô hình tương tự
                if model_name is None:
                    model_name = self._find_similar_model(organ)
                
                # Nếu có mô hình, sử dụng ràng buộc từ model_info
                if model_name is not None and model_name in model_constraints:
                    constraints = model_constraints[model_name]
                    
                    for metric_type, constraint_info in constraints.items():
                        limit = constraint_info.get('limit', 0)
                        priority = constraint_info.get('priority', 3)
                        weight = constraint_info.get('weight', 1.0)
                        
                        # Tạo mục tiêu dựa trên loại metric
                        if metric_type == 'D_mean':
                            optimization_goals.append(
                                OptimizationGoal(
                                    structure_name=organ,
                                    goal_type=OptimizationGoal.TYPE_MEAN_DOSE,
                                    dose_value=limit,
                                    weight=weight,
                                    priority=priority
                                )
                            )
                        elif metric_type == 'D_max':
                            optimization_goals.append(
                                OptimizationGoal(
                                    structure_name=organ,
                                    goal_type=OptimizationGoal.TYPE_MAX_DOSE,
                                    dose_value=limit,
                                    weight=weight,
                                    priority=priority
                                )
                            )
                        elif metric_type.startswith('V') and 'Gy' in metric_type:
                            # Xử lý các metric dạng V20Gy, V30Gy
                            dose_level = float(metric_type.replace('V', '').replace('Gy', ''))
                            volume_value = limit
                            
                            optimization_goals.append(
                                OptimizationGoal(
                                    structure_name=organ,
                                    goal_type=OptimizationGoal.TYPE_MAX_DVH,
                                    dose_value=dose_level,
                                    volume_value=volume_value,
                                    weight=weight,
                                    priority=priority
                                )
                            )
                        elif metric_type.startswith('D') and 'cc' in metric_type:
                            # Xử lý các metric dạng D1cc, D2cc
                            volume_cc = float(metric_type.replace('D', '').replace('cc', ''))
                            
                            # Tính thể tích tương đối dựa trên thể tích cơ quan
                            organ_mask = structures[organ]
                            voxel_size = plan_data.get('voxel_size', [1.0, 1.0, 1.0])  # mm
                            voxel_volume_cc = np.prod(voxel_size) / 1000  # mm³ -> cc
                            organ_volume_cc = np.sum(organ_mask) * voxel_volume_cc
                            
                            if organ_volume_cc > 0:
                                volume_percent = (volume_cc / organ_volume_cc) * 100
                                
                                optimization_goals.append(
                                    OptimizationGoal(
                                        structure_name=organ,
                                        goal_type=OptimizationGoal.TYPE_MAX_DVH,
                                        dose_value=limit,
                                        volume_value=volume_percent,
                                        weight=weight,
                                        priority=priority
                                    )
                                )
                    
                    self.logger.info(f"Đã thêm ràng buộc từ model_info cho {organ} dựa trên mô hình {model_name}")
                else:
                    # Nếu không có mô hình, sử dụng dự đoán
                    dose_metrics = self.predict_dose_metrics(features, organ)
                    if not dose_metrics:
                        continue
                    
                    # Xác định ưu tiên cho cơ quan
                    priority = 5  # Mặc định
                    for key, pri in default_oar_priority.items():
                        if key.lower() in organ.lower():
                            priority = pri
                            break
                    
                    # Tạo mục tiêu tối ưu hóa từ dự đoán
                    if 'D_mean' in dose_metrics:
                        optimization_goals.append(OptimizationGoal(
                            structure_name=organ,
                            goal_type=OptimizationGoal.TYPE_MEAN_DOSE,
                            dose_value=dose_metrics['D_mean'],
                            weight=1.0,
                            priority=priority
                        ))
                    
                    if 'D_max' in dose_metrics:
                        optimization_goals.append(OptimizationGoal(
                            structure_name=organ,
                            goal_type=OptimizationGoal.TYPE_MAX_DOSE,
                            dose_value=dose_metrics['D_max'],
                            weight=1.0,
                            priority=priority
                        ))
                    
                    self.logger.info(f"Đã thêm ràng buộc dựa trên dự đoán cho {organ}")
            
            return optimization_goals
            
        except Exception as e:
            import traceback
            self.logger.error(f"Lỗi khi đề xuất mục tiêu tối ưu hóa: {str(e)}")
            self.logger.error(traceback.format_exc())
            return optimization_goals
    
    def train_model(self, dataset: pd.DataFrame, organ_name: str, 
                   features: List[str], targets: List[str], 
                   test_size: float = 0.2, save_model: bool = True) -> Dict[str, Any]:
        """
        Huấn luyện mô hình KBP mới cho một cơ quan cụ thể.
        
        Args:
            dataset: DataFrame chứa dữ liệu huấn luyện
            organ_name: Tên cơ quan
            features: Danh sách các cột đặc trưng
            targets: Danh sách các cột mục tiêu
            test_size: Tỉ lệ dữ liệu kiểm tra
            save_model: Có lưu mô hình sau khi huấn luyện không
            
        Returns:
            Dictionary chứa kết quả đánh giá mô hình
        """
        results = {}
        
        try:
            # Chuẩn bị dữ liệu
            X = dataset[features]
            y = dataset[targets]
            
            # Chia dữ liệu huấn luyện và kiểm tra
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
            
            # Chuẩn hóa dữ liệu
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Huấn luyện mô hình
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Đánh giá mô hình
            y_pred = model.predict(X_test_scaled)
            
            # Tính các chỉ số đánh giá
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            results = {
                'mean_squared_error': mse,
                'mean_absolute_error': mae,
                'r2_score': r2
            }
            
            self.logger.info(f"Mô hình {organ_name} - MSE: {mse:.4f}, MAE: {mae:.4f}, R2: {r2:.4f}")
            
            # Lưu mô hình
            if save_model:
                model_data = {
                    'model': model,
                    'scaler': scaler,
                    'feature_columns': features,
                    'target_columns': targets,
                    'evaluation': results
                }
                
                os.makedirs(self.model_path, exist_ok=True)
                model_file = os.path.join(self.model_path, f"{organ_name}_model.pkl")
                
                with open(model_file, 'wb') as f:
                    pickle.dump(model_data, f)
                
                # Cập nhật thông tin mô hình
                info_path = os.path.join(self.model_path, f"{organ_name}_info.json")
                model_info = {}
                if os.path.exists(info_path):
                    with open(info_path, 'r') as f:
                        model_info = json.load(f)
                
                model_info['feature_columns'] = features
                model_info['target_columns'] = targets
                model_info['last_updated'] = pd.Timestamp.now().isoformat()
                
                with open(info_path, 'w') as f:
                    json.dump(model_info, f, indent=4)
                
                self.logger.info(f"Đã lưu mô hình {organ_name}")
                
                # Cập nhật model trong bộ nhớ
                self.models[organ_name] = model
                self.scalers[organ_name] = scaler
                self.feature_columns = features
                self.target_columns = targets
                
                if organ_name not in self.available_models:
                    self.available_models.append(organ_name)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Lỗi khi huấn luyện mô hình cho {organ_name}: {str(e)}")
            return results
    
    def extract_training_data_from_db(self) -> pd.DataFrame:
        """
        Trích xuất dữ liệu huấn luyện từ cơ sở dữ liệu bệnh nhân.
        
        Returns:
            DataFrame chứa dữ liệu huấn luyện
        """
        try:
            training_data = []
            
            # Lấy danh sách bệnh nhân
            patients = self.db.get_all_patients()
            if not patients:
                self.logger.warning("Không tìm thấy bệnh nhân nào trong cơ sở dữ liệu")
                return pd.DataFrame()
            
            for patient_info in patients:
                patient_id = patient_info.get('patient_id')
                if not patient_id:
                    continue
                
                # Tải thông tin chi tiết của bệnh nhân
                patient = self.db.get_patient(patient_id)
                if not patient:
                    continue
                
                # Lấy danh sách kế hoạch của bệnh nhân
                for plan_id, plan_data in patient.plans.items():
                    # Kiểm tra xem kế hoạch có dữ liệu DVH không
                    if not plan_data.get('dvh_data'):
                        continue
                    
                    # Lấy thông tin kế hoạch
                    plan_info = {
                        'patient_id': patient_id,
                        'plan_id': plan_id,
                        'total_dose': plan_data.get('total_dose', 0),
                        'fraction_count': plan_data.get('fraction_count', 0),
                        'technique': plan_data.get('technique', 'VMAT')
                    }
                    
                    # Lấy dữ liệu cấu trúc
                    structures = patient.structures
                    
                    # Trích xuất đặc trưng từ cấu trúc và kế hoạch
                    features = self.extract_features(structures, plan_info)
                    
                    if features.empty:
                        continue
                    
                    # Lấy dữ liệu DVH
                    dvh_data = plan_data.get('dvh_data', {})
                    
                    # Kết hợp dữ liệu
                    for organ_name, dvh in dvh_data.items():
                        if organ_name.startswith('PTV') or organ_name.startswith('CTV') or organ_name.startswith('GTV'):
                            continue
                        
                        # Trích xuất các chỉ số liều từ DVH
                        dose_metrics = dvh.get('dose_metrics', {})
                        volume_metrics = dvh.get('volume_metrics', {})
                        
                        if not dose_metrics and not volume_metrics:
                            continue
                        
                        # Tạo bản ghi dữ liệu huấn luyện
                        data_record = {
                            'patient_id': patient_id,
                            'plan_id': plan_id,
                            'organ_name': organ_name,
                            'total_dose': plan_info.get('total_dose', 0),
                            'fraction_count': plan_info.get('fraction_count', 0),
                            'technique': plan_info.get('technique', 'VMAT')
                        }
                        
                        # Bổ sung các đặc trưng khác
                        for feature_col in features.columns:
                            data_record[feature_col] = features.iloc[0][feature_col]
                        
                        # Bổ sung dữ liệu liều
                        for metric, value in dose_metrics.items():
                            data_record[metric] = value
                        
                        # Bổ sung dữ liệu thể tích
                        for metric, value in volume_metrics.items():
                            data_record[metric] = value
                        
                        training_data.append(data_record)
            
            # Tạo DataFrame từ dữ liệu đã thu thập
            if not training_data:
                self.logger.warning("Không tìm thấy dữ liệu huấn luyện phù hợp")
                return pd.DataFrame()
            
            df = pd.DataFrame(training_data)
            self.logger.info(f"Đã trích xuất {len(df)} bản ghi dữ liệu huấn luyện")
            return df
            
        except Exception as e:
            self.logger.error(f"Lỗi khi trích xuất dữ liệu huấn luyện: {str(e)}")
            return pd.DataFrame()
    
    def plot_model_evaluation(self, organ_name: str, actual: np.ndarray, predicted: np.ndarray, 
                             target_names: List[str], save_path: Optional[str] = None):
        """
        Vẽ biểu đồ đánh giá mô hình.
        
        Args:
            organ_name: Tên cơ quan
            actual: Giá trị thực tế
            predicted: Giá trị dự đoán
            target_names: Tên các biến mục tiêu
            save_path: Đường dẫn lưu biểu đồ (nếu cần)
        """
        try:
            n_targets = len(target_names)
            fig, axes = plt.subplots(1, n_targets, figsize=(5*n_targets, 4))
            
            if n_targets == 1:
                axes = [axes]
            
            for i, name in enumerate(target_names):
                ax = axes[i]
                
                # Vẽ scatter plot
                ax.scatter(actual[:, i], predicted[:, i], alpha=0.5)
                
                # Vẽ đường y=x
                min_val = min(actual[:, i].min(), predicted[:, i].min())
                max_val = max(actual[:, i].max(), predicted[:, i].max())
                ax.plot([min_val, max_val], [min_val, max_val], 'r--')
                
                # Tính R2
                r2 = r2_score(actual[:, i], predicted[:, i])
                
                ax.set_xlabel('Giá trị thực tế')
                ax.set_ylabel('Giá trị dự đoán')
                ax.set_title(f'{name} (R² = {r2:.3f})')
                ax.grid(True, alpha=0.3)
            
            plt.suptitle(f'Đánh giá mô hình KBP cho {organ_name}')
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                plt.close()
            else:
                plt.show()
                
        except Exception as e:
            self.logger.error(f"Lỗi khi vẽ biểu đồ đánh giá: {str(e)}")
