#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <map>
#include <memory>
#include <numeric>
#include <fstream>
#include <sstream>
#include <random>
#include <chrono>

// Cấu trúc để lưu các mục tiêu cho từng cấu trúc
struct ObjectiveFunction {
    enum Type {
        MAX_DOSE,         // Liều tối đa
        MIN_DOSE,         // Liều tối thiểu
        MAX_DVH,          // Liều tối đa cho x% thể tích
        MIN_DVH,          // Liều tối thiểu cho x% thể tích
        MEAN_DOSE,        // Liều trung bình
        CONFORMITY,       // Độ tương thích của liều với cấu trúc
        HOMOGENEITY,      // Độ đồng nhất liều trong cấu trúc
        UNIFORMITY        // Độ đều liều trong cấu trúc
    };
    
    std::string structure_name;    // Tên cấu trúc
    Type type;                     // Loại mục tiêu
    double dose;                   // Giá trị liều mục tiêu (Gy)
    double volume_percent;         // Phần trăm thể tích (cho DVH)
    double weight;                 // Trọng số, càng cao càng quan trọng
    
    ObjectiveFunction(const std::string& name, Type t, double d, double vol = 0.0, double w = 1.0) 
        : structure_name(name), type(t), dose(d), volume_percent(vol), weight(w) {}
};

// Lớp tối ưu hóa kế hoạch sử dụng thuật toán gradient descent
class GradientOptimizer {
private:
    std::vector<std::vector<std::vector<double>>> dose_matrix;  // Ma trận liều
    std::map<std::string, std::vector<std::vector<std::vector<int>>>> structure_masks; // Mặt nạ cấu trúc
    std::vector<ObjectiveFunction> objectives;     // Danh sách mục tiêu
    std::vector<std::vector<double>> beam_weights; // Trọng số chùm tia
    double learning_rate;                          // Tốc độ học
    int max_iterations;                            // Số lần lặp tối đa
    double convergence_threshold;                  // Ngưỡng hội tụ
    
    // Ma trận liều của từng chùm tia
    std::vector<std::vector<std::vector<std::vector<double>>>> beam_dose_matrices;
    
public:
    GradientOptimizer(
        const std::vector<std::vector<std::vector<double>>>& dose_matrix,
        const std::map<std::string, std::vector<std::vector<std::vector<int>>>>& structure_masks,
        double learning_rate = 0.01,
        int max_iterations = 100,
        double convergence_threshold = 1e-4
    ) : dose_matrix(dose_matrix), structure_masks(structure_masks),
        learning_rate(learning_rate), max_iterations(max_iterations),
        convergence_threshold(convergence_threshold) {}
    
    // Thêm mục tiêu để tối ưu hóa
    void add_objective(const ObjectiveFunction& objective) {
        objectives.push_back(objective);
    }
    
    // Thêm ma trận liều của từng chùm tia
    void add_beam_dose_matrix(const std::vector<std::vector<std::vector<double>>>& beam_dose) {
        beam_dose_matrices.push_back(beam_dose);
    }
    
    // Khởi tạo trọng số chùm tia ban đầu (đều nhau)
    void initialize_beam_weights() {
        int num_beams = beam_dose_matrices.size();
        if (num_beams > 0) {
            beam_weights.resize(num_beams, std::vector<double>(1, 1.0 / num_beams));
        }
    }
    
    // Tính hàm mục tiêu (mục tiêu càng thấp càng tốt)
    double calculate_objective_function() {
        double total_objective = 0.0;
        
        // Tính toán liều tổng dựa trên trọng số hiện tại
        auto total_dose = calculate_total_dose();
        
        // Đánh giá mỗi mục tiêu
        for (const auto& objective : objectives) {
            double objective_value = 0.0;
            
            // Lấy mặt nạ cấu trúc
            const auto& mask = structure_masks.at(objective.structure_name);
            
            // Tạo vector liều cho các voxel trong cấu trúc
            std::vector<double> structure_doses;
            for (size_t z = 0; z < total_dose.size(); ++z) {
                for (size_t y = 0; y < total_dose[z].size(); ++y) {
                    for (size_t x = 0; x < total_dose[z][y].size(); ++x) {
                        if (z < mask.size() && y < mask[z].size() && x < mask[z][y].size() && mask[z][y][x] > 0) {
                            structure_doses.push_back(total_dose[z][y][x]);
                        }
                    }
                }
            }
            
            // Sắp xếp các liều để tính DVH
            std::sort(structure_doses.begin(), structure_doses.end());
            
            // Tính giá trị mục tiêu theo loại
            switch (objective.type) {
                case ObjectiveFunction::MAX_DOSE: {
                    // Mục tiêu: Liều tối đa <= mục tiêu
                    double max_dose = structure_doses.empty() ? 0.0 : structure_doses.back();
                    if (max_dose > objective.dose) {
                        objective_value = std::pow(max_dose - objective.dose, 2);
                    }
                    break;
                }
                case ObjectiveFunction::MIN_DOSE: {
                    // Mục tiêu: Liều tối thiểu >= mục tiêu
                    double min_dose = structure_doses.empty() ? 0.0 : structure_doses.front();
                    if (min_dose < objective.dose) {
                        objective_value = std::pow(objective.dose - min_dose, 2);
                    }
                    break;
                }
                case ObjectiveFunction::MAX_DVH: {
                    // Mục tiêu: Liều ở % thể tích <= mục tiêu
                    if (!structure_doses.empty()) {
                        size_t index = static_cast<size_t>((1.0 - objective.volume_percent / 100.0) * structure_doses.size());
                        index = std::min(index, structure_doses.size() - 1);
                        double dose_at_volume = structure_doses[index];
                        if (dose_at_volume > objective.dose) {
                            objective_value = std::pow(dose_at_volume - objective.dose, 2);
                        }
                    }
                    break;
                }
                case ObjectiveFunction::MIN_DVH: {
                    // Mục tiêu: Liều ở % thể tích >= mục tiêu
                    if (!structure_doses.empty()) {
                        size_t index = static_cast<size_t>((objective.volume_percent / 100.0) * structure_doses.size());
                        index = std::min(index, structure_doses.size() - 1);
                        double dose_at_volume = structure_doses[index];
                        if (dose_at_volume < objective.dose) {
                            objective_value = std::pow(objective.dose - dose_at_volume, 2);
                        }
                    }
                    break;
                }
                case ObjectiveFunction::MEAN_DOSE: {
                    // Mục tiêu: Liều trung bình = mục tiêu
                    if (!structure_doses.empty()) {
                        double mean_dose = std::accumulate(structure_doses.begin(), structure_doses.end(), 0.0) / structure_doses.size();
                        objective_value = std::pow(mean_dose - objective.dose, 2);
                    }
                    break;
                }
                case ObjectiveFunction::CONFORMITY: {
                    // Mục tiêu: Độ tương thích cao (liều trong PTV cao, ngoài PTV thấp)
                    // Chỉ số đơn giản: tỷ lệ thể tích nhận >= 95% liều mục tiêu nằm trong PTV
                    
                    // TODO: Triển khai chỉ số tương thích thực tế (cần thông tin về liều bên ngoài PTV)
                    objective_value = 0.0;
                    break;
                }
                case ObjectiveFunction::HOMOGENEITY: {
                    // Mục tiêu: Độ đồng nhất cao (chênh lệch liều trong PTV thấp)
                    if (structure_doses.size() > 1) {
                        double d98 = structure_doses[static_cast<size_t>(0.02 * structure_doses.size())];
                        double d2 = structure_doses[static_cast<size_t>(0.98 * structure_doses.size())];
                        double homogeneity_index = d2 / d98;
                        // Mục tiêu: HI càng gần 1 càng tốt
                        objective_value = std::pow(homogeneity_index - 1.0, 2) * 100;
                    }
                    break;
                }
                case ObjectiveFunction::UNIFORMITY: {
                    // Mục tiêu: Độ đều (std deviation thấp)
                    if (structure_doses.size() > 1) {
                        double mean = std::accumulate(structure_doses.begin(), structure_doses.end(), 0.0) / structure_doses.size();
                        double sq_sum = std::inner_product(structure_doses.begin(), structure_doses.end(), structure_doses.begin(), 0.0);
                        double std_dev = std::sqrt(sq_sum / structure_doses.size() - mean * mean);
                        objective_value = std::pow(std_dev / mean, 2) * 100;
                    }
                    break;
                }
            }
            
            // Cộng vào mục tiêu tổng với trọng số
            total_objective += objective_value * objective.weight;
        }
        
        return total_objective;
    }
    
    // Tính tổng liều dựa trên trọng số chùm tia hiện tại
    std::vector<std::vector<std::vector<double>>> calculate_total_dose() {
        // Sao chép kích thước từ ma trận liều
        auto total_dose = dose_matrix;
        std::fill(total_dose.begin(), total_dose.end(), std::vector<std::vector<double>>(
            total_dose[0].size(), std::vector<double>(total_dose[0][0].size(), 0.0)
        ));
        
        // Cộng liều từ mỗi chùm tia với trọng số tương ứng
        for (size_t b = 0; b < beam_dose_matrices.size(); ++b) {
            for (size_t c = 0; c < beam_weights[b].size(); ++c) {
                double weight = beam_weights[b][c];
                for (size_t z = 0; z < total_dose.size(); ++z) {
                    for (size_t y = 0; y < total_dose[z].size(); ++y) {
                        for (size_t x = 0; x < total_dose[z][y].size(); ++x) {
                            if (z < beam_dose_matrices[b].size() && 
                                y < beam_dose_matrices[b][z].size() && 
                                x < beam_dose_matrices[b][z][y].size()) {
                                total_dose[z][y][x] += weight * beam_dose_matrices[b][z][y][x];
                            }
                        }
                    }
                }
            }
        }
        
        return total_dose;
    }
    
    // Tính gradient cho mỗi trọng số chùm tia
    std::vector<std::vector<double>> calculate_gradient() {
        // Ma trận gradient có cùng kích thước với trọng số chùm tia
        std::vector<std::vector<double>> gradient(beam_weights.size());
        for (size_t b = 0; b < gradient.size(); ++b) {
            gradient[b].resize(beam_weights[b].size(), 0.0);
        }
        
        // Tính liều tổng hiện tại
        auto current_dose = calculate_total_dose();
        
        // Tính giá trị mục tiêu hiện tại
        double current_objective = calculate_objective_function();
        
        // Tính gradient số bằng phương pháp sai phân hữu hạn
        const double delta = 1e-5;
        
        for (size_t b = 0; b < beam_weights.size(); ++b) {
            for (size_t c = 0; c < beam_weights[b].size(); ++c) {
                // Tăng trọng số một chút
                beam_weights[b][c] += delta;
                
                // Tính lại mục tiêu
                double perturbed_objective = calculate_objective_function();
                
                // Tính gradient
                gradient[b][c] = (perturbed_objective - current_objective) / delta;
                
                // Khôi phục trọng số
                beam_weights[b][c] -= delta;
            }
        }
        
        return gradient;
    }
    
    // Thuật toán tối ưu hóa gradient descent
    void optimize() {
        // Khởi tạo trọng số chùm tia nếu chưa có
        if (beam_weights.empty()) {
            initialize_beam_weights();
        }
        
        double prev_objective = std::numeric_limits<double>::max();
        
        for (int iter = 0; iter < max_iterations; ++iter) {
            // Tính giá trị mục tiêu hiện tại
            double current_objective = calculate_objective_function();
            
            // In ra tiến trình
            std::cout << "Lần lặp " << iter << ": Giá trị mục tiêu = " << current_objective << std::endl;
            
            // Kiểm tra hội tụ
            if (std::abs(prev_objective - current_objective) < convergence_threshold) {
                std::cout << "Đã hội tụ sau " << iter << " lần lặp." << std::endl;
                break;
            }
            
            prev_objective = current_objective;
            
            // Tính gradient
            auto gradient = calculate_gradient();
            
            // Cập nhật trọng số theo hướng ngược gradient
            for (size_t b = 0; b < beam_weights.size(); ++b) {
                for (size_t c = 0; c < beam_weights[b].size(); ++c) {
                    beam_weights[b][c] -= learning_rate * gradient[b][c];
                    
                    // Đảm bảo trọng số không âm
                    beam_weights[b][c] = std::max(0.0, beam_weights[b][c]);
                }
            }
            
            // Chuẩn hóa trọng số (tổng = 1.0)
            normalize_weights();
        }
    }
    
    // Chuẩn hóa trọng số để tổng bằng 1
    void normalize_weights() {
        double sum = 0.0;
        
        // Tính tổng tất cả trọng số
        for (const auto& beam_weight : beam_weights) {
            sum += std::accumulate(beam_weight.begin(), beam_weight.end(), 0.0);
        }
        
        // Chia tất cả trọng số cho tổng
        if (sum > 0.0) {
            for (auto& beam_weight : beam_weights) {
                for (auto& weight : beam_weight) {
                    weight /= sum;
                }
            }
        } else {
            // Nếu tổng bằng 0, đặt trọng số đều nhau
            double equal_weight = 1.0 / (beam_weights.size() * beam_weights[0].size());
            for (auto& beam_weight : beam_weights) {
                std::fill(beam_weight.begin(), beam_weight.end(), equal_weight);
            }
        }
    }
    
    // Lấy trọng số chùm tia tối ưu
    const std::vector<std::vector<double>>& get_optimized_weights() const {
        return beam_weights;
    }
};

// Lớp tối ưu hóa sử dụng thuật toán di truyền (Genetic Algorithm)
class GeneticOptimizer {
private:
    std::vector<std::vector<std::vector<double>>> dose_matrix;
    std::map<std::string, std::vector<std::vector<std::vector<int>>>> structure_masks;
    std::vector<ObjectiveFunction> objectives;
    std::vector<std::vector<std::vector<double>>> beam_dose_matrices;
    
    int population_size;
    int max_generations;
    double mutation_rate;
    double crossover_rate;
    
    std::vector<std::vector<double>> population;  // Mỗi cá thể là một vector trọng số chùm tia
    std::vector<double> fitness;                 // Độ thích nghi của mỗi cá thể (càng thấp càng tốt)
    
public:
    GeneticOptimizer(
        const std::vector<std::vector<std::vector<double>>>& dose_matrix,
        const std::map<std::string, std::vector<std::vector<std::vector<int>>>>& structure_masks,
        int population_size = 50,
        int max_generations = 100,
        double mutation_rate = 0.1,
        double crossover_rate = 0.8
    ) : dose_matrix(dose_matrix), structure_masks(structure_masks),
        population_size(population_size), max_generations(max_generations),
        mutation_rate(mutation_rate), crossover_rate(crossover_rate) {}
    
    // (các phương thức tương tự như trong GradientOptimizer)
    
    // Khởi tạo quần thể ban đầu
    void initialize_population(int num_beams) {
        population.resize(population_size);
        
        // Khởi tạo ngẫu nhiên
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<> dis(0.0, 1.0);
        
        for (int i = 0; i < population_size; ++i) {
            population[i].resize(num_beams);
            
            // Khởi tạo với giá trị ngẫu nhiên
            for (int j = 0; j < num_beams; ++j) {
                population[i][j] = dis(gen);
            }
            
            // Chuẩn hóa để tổng bằng 1
            double sum = std::accumulate(population[i].begin(), population[i].end(), 0.0);
            for (int j = 0; j < num_beams; ++j) {
                population[i][j] /= sum;
            }
        }
        
        // Khởi tạo mảng độ thích nghi
        fitness.resize(population_size);
    }
    
    // Chạy thuật toán tối ưu hóa
    std::vector<double> optimize() {
        // TODO: Triển khai thuật toán di truyền
        return std::vector<double>();
    }
};

// Hàm chính để chạy từ Python
extern "C" {
    void run_gradient_optimization(
        double* dose_matrix_flat, int* matrix_dims,
        int* structure_masks_flat, int* structure_masks_dims,
        char** structure_names, int num_structures,
        ObjectiveFunction* objectives, int num_objectives,
        double* beam_dose_matrices_flat, int* beam_dose_matrices_dims, int num_beams,
        double* optimized_weights, int* weights_dims,
        double learning_rate, int max_iterations, double convergence_threshold
    ) {
        // TODO: Chuyển đổi dữ liệu từ Python sang C++ rồi chạy tối ưu hóa
    }
}
