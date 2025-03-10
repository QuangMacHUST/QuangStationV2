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

from quangstation.utils.logging import get_logger
from quangstation.utils.config import get_config
from quangstation.data_management.patient_db import PatientDatabase
from quangstation.optimization.goal_optimizer import OptimizationGoal

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
        self.config = get_config()
        self.logger = get_logger("KBP_Optimizer")
        self.model_path = model_path
        self.models = {}  # Mô hình cho từng loại cơ quan
        self.scalers = {}  # Scalers cho từng loại cơ quan
        self.available_models = []  # Danh sách các mô hình có sẵn
        self.feature_columns = []  # Các cột đặc trưng sử dụng trong mô hình
        self.target_columns = []  # Các cột mục tiêu để dự đoán
        self.db = PatientDatabase()
        
        # Thiết lập đường dẫn lưu mô hình mặc định
        if not model_path:
            self.model_path = os.path.join(
                self.config.get("app_data_dir", os.path.expanduser("~/.quangstation")),
                "models"
            )
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
            model_file = os.path.join(self.model_path, f"{organ_name}.pkl")
            if not os.path.exists(model_file):
                self.logger.warning(f"Không tìm thấy mô hình cho {organ_name}")
                return False
            
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
                self.models[organ_name] = model_data['model']
                self.scalers[organ_name] = model_data['scaler']
                if 'feature_columns' in model_data:
                    self.feature_columns = model_data['feature_columns']
                if 'target_columns' in model_data:
                    self.target_columns = model_data['target_columns']
            
            self.logger.info(f"Đã tải mô hình KBP cho {organ_name}")
            return True
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
        """Tìm mô hình tương tự cho một cơ quan nếu không có mô hình chính xác."""
        # Chuẩn hóa tên cơ quan
        organ_lower = organ_name.lower()
        
        # Danh sách từ khóa liên quan
        keywords = {
            'parotid': ['parotid', 'tuyến mang tai'],
            'spinal_cord': ['spinal', 'cord', 'tủy sống'],
            'brainstem': ['brain', 'stem', 'thân não'],
            'lung': ['lung', 'phổi'],
            'heart': ['heart', 'tim'],
            'liver': ['liver', 'gan'],
            'kidney': ['kidney', 'thận'],
            'lens': ['lens', 'thủy tinh thể'],
            'optic_nerve': ['optic', 'nerve', 'thần kinh thị giác']
        }
        
        for model in self.available_models:
            model_lower = model.lower()
            
            # Nếu có từ khóa trùng khớp
            for key, words in keywords.items():
                if any(word in organ_lower for word in words) and any(word in model_lower for word in words):
                    self.logger.info(f"Đã tìm thấy mô hình tương tự '{model}' cho cơ quan '{organ_name}'")
                    return model
        
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
            # Trích xuất đặc trưng
            features = self.extract_features(structures, plan_data)
            if features.empty:
                self.logger.warning("Không thể trích xuất đặc trưng")
                return optimization_goals
            
            # Danh sách ưu tiên cơ quan
            oar_priority = {
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
                'Lips': 4
            }
            
            # Danh sách cơ quan trong kế hoạch
            organs = [name for name in structures.keys() 
                      if not (name.startswith('PTV') or name.startswith('CTV') or name.startswith('GTV'))]
            
            for organ in organs:
                # Dự đoán chỉ số liều
                dose_metrics = self.predict_dose_metrics(features, organ)
                if not dose_metrics:
                    continue
                
                # Xác định ưu tiên cho cơ quan
                priority = 5  # Mặc định
                for key, pri in oar_priority.items():
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
                
                # Thêm ràng buộc DVH nếu có
                for key, value in dose_metrics.items():
                    if key.startswith('D'):
                        try:
                            # Trích xuất giá trị phần trăm từ D<X>
                            volume_value = float(key.split('_')[1].replace('D', ''))
                            if 0 <= volume_value <= 100:
                                optimization_goals.append(OptimizationGoal(
                                    structure_name=organ,
                                    goal_type=OptimizationGoal.TYPE_MAX_DVH,
                                    dose_value=value,
                                    volume_value=volume_value,
                                    weight=1.0,
                                    priority=priority
                                ))
                        except:
                            pass
                    
                    if key.startswith('V'):
                        try:
                            # Trích xuất giá trị liều từ V<X>
                            dose_value = float(key.split('_')[1].replace('V', ''))
                            optimization_goals.append(OptimizationGoal(
                                structure_name=organ,
                                goal_type=OptimizationGoal.TYPE_MIN_DVH,
                                dose_value=dose_value,
                                volume_value=value,
                                weight=1.0,
                                priority=priority
                            ))
                        except:
                            pass
            
            # Thêm mục tiêu cho PTV
            for name in structures.keys():
                if name.startswith('PTV'):
                    prescribed_dose = plan_data.get('total_dose', 0)
                    if prescribed_dose > 0:
                        # Mục tiêu liều tối thiểu
                        optimization_goals.append(OptimizationGoal(
                            structure_name=name,
                            goal_type=OptimizationGoal.TYPE_MIN_DOSE,
                            dose_value=prescribed_dose * 0.95,  # 95% liều kê toa
                            weight=10.0,
                            priority=1,
                            is_required=True
                        ))
                        
                        # Mục tiêu liều tối đa
                        optimization_goals.append(OptimizationGoal(
                            structure_name=name,
                            goal_type=OptimizationGoal.TYPE_MAX_DOSE,
                            dose_value=prescribed_dose * 1.07,  # 107% liều kê toa
                            weight=8.0,
                            priority=1,
                            is_required=True
                        ))
                        
                        # Mục tiêu liều đồng đều
                        optimization_goals.append(OptimizationGoal(
                            structure_name=name,
                            goal_type=OptimizationGoal.TYPE_UNIFORM_DOSE,
                            dose_value=prescribed_dose,
                            weight=5.0,
                            priority=2
                        ))
            
            return optimization_goals
            
        except Exception as e:
            self.logger.error(f"Lỗi khi đề xuất mục tiêu tối ưu hóa: {str(e)}")
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
                model_file = os.path.join(self.model_path, f"{organ_name}.pkl")
                
                with open(model_file, 'wb') as f:
                    pickle.dump(model_data, f)
                
                # Cập nhật thông tin mô hình
                info_path = os.path.join(self.model_path, "model_info.json")
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
            # Lấy danh sách bệnh nhân có kế hoạch xạ trị
            patients = self.db.get_all_patients()
            
            training_data = []
            
            for patient in patients:
                patient_id = patient.get('id')
                plans = self.db.get_patient_plans(patient_id)
                
                for plan in plans:
                    plan_id = plan.get('id')
                    
                    # Kiểm tra xem kế hoạch có dữ liệu DVH không
                    if not plan.get('dvh_data'):
                        continue
                    
                    # Lấy thông tin kế hoạch
                    plan_data = {
                        'patient_id': patient_id,
                        'plan_id': plan_id,
                        'total_dose': plan.get('total_dose', 0),
                        'fraction_count': plan.get('fraction_count', 0),
                        'technique': plan.get('technique', 'VMAT')
                    }
                    
                    # Lấy dữ liệu cấu trúc và đặc trưng
                    structures = self.db.get_plan_structures(plan_id)
                    features = self.extract_features(structures, plan_data)
                    
                    if features.empty:
                        continue
                    
                    # Lấy dữ liệu DVH
                    dvh_data = plan.get('dvh_data', {})
                    
                    # Kết hợp dữ liệu
                    for organ_name, dvh in dvh_data.items():
                        if organ_name.startswith('PTV') or organ_name.startswith('CTV') or organ_name.startswith('GTV'):
                            continue
                        
                        # Trích xuất các chỉ số liều từ DVH
                        organ_data = {**plan_data}
                        
                        if 'mean' in dvh:
                            organ_data[f'{organ_name}_D_mean'] = dvh['mean']
                        
                        if 'max' in dvh:
                            organ_data[f'{organ_name}_D_max'] = dvh['max']
                        
                        if 'min' in dvh:
                            organ_data[f'{organ_name}_D_min'] = dvh['min']
                        
                        # Thêm các giá trị D<x> và V<x>
                        if 'cum_dvh' in dvh:
                            cum_dvh = dvh['cum_dvh']
                            doses = cum_dvh['doses']
                            volumes = cum_dvh['volumes']
                            
                            for vol_percent in [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98]:
                                # Tính D<vol_percent>
                                try:
                                    idx = next(i for i, v in enumerate(volumes) if v <= vol_percent)
                                    organ_data[f'{organ_name}_D_{vol_percent}'] = doses[idx]
                                except:
                                    pass
                            
                            for dose_percent in [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98]:
                                # Tính V<dose_percent>
                                prescribed_dose = plan.get('total_dose', 0)
                                if prescribed_dose > 0:
                                    dose_val = prescribed_dose * dose_percent / 100
                                    try:
                                        idx = next(i for i, d in enumerate(doses) if d >= dose_val)
                                        organ_data[f'{organ_name}_V_{dose_percent}'] = volumes[idx]
                                    except:
                                        pass
                        
                        # Kết hợp với đặc trưng
                        combined_data = {**organ_data, **features.iloc[0].to_dict()}
                        training_data.append(combined_data)
            
            return pd.DataFrame(training_data)
            
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
