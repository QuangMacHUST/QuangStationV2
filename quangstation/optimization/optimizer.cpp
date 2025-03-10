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
                    
                    // Triển khai chỉ số tương thích thực tế (Paddick Conformity Index)
                    // Paddick CI = (TV_PIV)² / (TV × PIV)
                    // TV_PIV: thể tích đích nhận liều kê toa
                    // TV: thể tích đích
                    // PIV: thể tích nhận liều kê toa
                    
                    // Tìm tất cả các voxel nhận ít nhất liều kê toa (PIV)
                    double prescribed_dose = objective.dose;
                    int piv_volume = 0;  // Thể tích nhận liều kê toa
                    int tv_volume = 0;   // Thể tích đích
                    int tv_piv_volume = 0; // Thể tích đích nhận liều kê toa
                    
                    // Tính các thể tích
                    for (size_t i = 0; i < total_dose.size(); ++i) {
                        for (size_t j = 0; j < total_dose[i].size(); ++j) {
                            for (size_t k = 0; k < total_dose[i][j].size(); ++k) {
                                // Kiểm tra xem voxel có nằm trong PTV không
                                bool is_in_target = mask[i][j][k] > 0;
                                
                                // Kiểm tra xem voxel có nhận đủ liều không
                                bool is_in_piv = total_dose[i][j][k] >= prescribed_dose;
                                
                                // Cập nhật các thể tích
                                if (is_in_target) {
                                    tv_volume++;
                                }
                                
                                if (is_in_piv) {
                                    piv_volume++;
                                }
                                
                                if (is_in_target && is_in_piv) {
                                    tv_piv_volume++;
                                }
                            }
                        }
                    }
                    
                    // Tính chỉ số Paddick
                    double paddick_ci = 0.0;
                    if (tv_volume > 0 && piv_volume > 0) {
                        paddick_ci = std::pow(tv_piv_volume, 2) / (static_cast<double>(tv_volume) * piv_volume);
                    }
                    
                    // Mục tiêu là tối đa hóa chỉ số Paddick (gần 1.0)
                    // Chuyển thành bài toán tối thiểu hóa
                    objective_value = std::max(0.0, 1.0 - paddick_ci);
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
        // Triển khai thuật toán di truyền
        if (population.empty() || objectives.empty() || beam_dose_matrices.empty()) {
            std::cerr << "Dữ liệu không đủ để tối ưu hóa." << std::endl;
            return std::vector<double>();
        }
        
        // Khởi tạo bộ tạo số ngẫu nhiên
        std::random_device rd;
        std::mt19937 gen(rd());
        
        // Tính độ thích nghi cho quần thể ban đầu
        evaluate_fitness();
        
        // Theo dõi cá thể tốt nhất qua các thế hệ
        std::vector<double> best_individual;
        double best_fitness = std::numeric_limits<double>::max();
        
        // Chạy qua các thế hệ
        for (int generation = 0; generation < max_generations; ++generation) {
            // Lưu lại cá thể tốt nhất
            int best_idx = find_best_individual();
            if (fitness[best_idx] < best_fitness) {
                best_fitness = fitness[best_idx];
                best_individual = population[best_idx];
            }
            
            // In thông tin về thế hệ hiện tại
            if (generation % 10 == 0) {
                std::cout << "Thế hệ " << generation << ", độ thích nghi tốt nhất: " 
                          << best_fitness << std::endl;
            }
            
            // Tạo quần thể mới
            std::vector<std::vector<double>> new_population;
            
            // Giữ lại một số cá thể tốt nhất (elitism)
            int num_elites = static_cast<int>(population_size * 0.1); // 10% elites
            std::vector<int> elite_indices = find_elite_individuals(num_elites);
            for (int idx : elite_indices) {
                new_population.push_back(population[idx]);
            }
            
            // Tạo phần còn lại của quần thể qua chọn lọc, lai ghép và đột biến
            while (new_population.size() < population_size) {
                // Chọn 2 cá thể cha mẹ dựa trên độ thích nghi
                std::vector<double> parent1 = select_individual();
                std::vector<double> parent2 = select_individual();
                
                // Lai ghép nếu xác suất lai thỏa mãn
                std::vector<double> child1 = parent1;
                std::vector<double> child2 = parent2;
                
                if (std::uniform_real_distribution<double>(0.0, 1.0)(gen) < crossover_rate) {
                    std::tie(child1, child2) = crossover(parent1, parent2);
                }
                
                // Đột biến
                mutate(child1);
                mutate(child2);
                
                // Chuẩn hóa trọng số
                normalize_weights(child1);
                normalize_weights(child2);
                
                // Thêm vào quần thể mới
                new_population.push_back(child1);
                if (new_population.size() < population_size) {
                    new_population.push_back(child2);
                }
            }
            
            // Thay thế quần thể cũ
            population = std::move(new_population);
            
            // Tính lại độ thích nghi
            evaluate_fitness();
            
            // Kiểm tra điều kiện dừng (có thể thêm logic dừng sớm nếu cần)
            if (generation > 10 && best_fitness < 1e-4) {
                std::cout << "Đã đạt ngưỡng hội tụ, dừng tối ưu hóa tại thế hệ " << generation << std::endl;
                break;
            }
        }
        
        // Trả về cá thể tốt nhất
        return best_individual.empty() ? population[find_best_individual()] : best_individual;
    }

private:
    // Tính độ thích nghi cho tất cả các cá thể trong quần thể
    void evaluate_fitness() {
        for (size_t i = 0; i < population.size(); ++i) {
            fitness[i] = calculate_fitness(population[i]);
        }
    }
    
    // Tính độ thích nghi của một cá thể (trọng số chùm tia)
    double calculate_fitness(const std::vector<double>& weights) {
        // Tính tổng liều dựa trên trọng số chùm tia
        auto total_dose = calculate_total_dose(weights);
        
        double total_objective = 0.0;
        
        // Tính giá trị hàm mục tiêu
        for (const auto& objective : objectives) {
            // Tìm mặt nạ của cấu trúc
            auto mask_it = structure_masks.find(objective.structure_name);
            if (mask_it == structure_masks.end()) {
                std::cerr << "Không tìm thấy cấu trúc " << objective.structure_name << std::endl;
                continue;
            }
            
            const auto& mask = mask_it->second;
            double obj_value = 0.0;
            
            switch (objective.type) {
                case ObjectiveFunction::MAX_DOSE: {
                    double max_dose = 0.0;
                    for (size_t i = 0; i < total_dose.size(); ++i) {
                        for (size_t j = 0; j < total_dose[i].size(); ++j) {
                            for (size_t k = 0; k < total_dose[i][j].size(); ++k) {
                                if (mask[i][j][k] > 0 && total_dose[i][j][k] > max_dose) {
                                    max_dose = total_dose[i][j][k];
                                }
                            }
                        }
                    }
                    obj_value = std::max(0.0, max_dose - objective.dose);
                    break;
                }
                case ObjectiveFunction::MIN_DOSE: {
                    double min_dose = std::numeric_limits<double>::max();
                    for (size_t i = 0; i < total_dose.size(); ++i) {
                        for (size_t j = 0; j < total_dose[i].size(); ++j) {
                            for (size_t k = 0; k < total_dose[i][j].size(); ++k) {
                                if (mask[i][j][k] > 0 && total_dose[i][j][k] < min_dose) {
                                    min_dose = total_dose[i][j][k];
                                }
                            }
                        }
                    }
                    obj_value = std::max(0.0, objective.dose - min_dose);
                    break;
                }
                case ObjectiveFunction::MEAN_DOSE: {
                    double sum_dose = 0.0;
                    int count = 0;
                    for (size_t i = 0; i < total_dose.size(); ++i) {
                        for (size_t j = 0; j < total_dose[i].size(); ++j) {
                            for (size_t k = 0; k < total_dose[i][j].size(); ++k) {
                                if (mask[i][j][k] > 0) {
                                    sum_dose += total_dose[i][j][k];
                                    count++;
                                }
                            }
                        }
                    }
                    double mean_dose = count > 0 ? sum_dose / count : 0.0;
                    obj_value = std::pow(mean_dose - objective.dose, 2);
                    break;
                }
                case ObjectiveFunction::MAX_DVH: {
                    // Tính DVH và xác định liều cho phần trăm thể tích
                    std::vector<double> doses;
                    for (size_t i = 0; i < total_dose.size(); ++i) {
                        for (size_t j = 0; j < total_dose[i].size(); ++j) {
                            for (size_t k = 0; k < total_dose[i][j].size(); ++k) {
                                if (mask[i][j][k] > 0) {
                                    doses.push_back(total_dose[i][j][k]);
                                }
                            }
                        }
                    }
                    
                    if (!doses.empty()) {
                        std::sort(doses.begin(), doses.end());
                        int idx = static_cast<int>(doses.size() * (1.0 - objective.volume_percent / 100.0));
                        idx = std::min(std::max(0, idx), static_cast<int>(doses.size() - 1));
                        double actual_dose = doses[idx];
                        obj_value = std::max(0.0, actual_dose - objective.dose);
                    }
                    break;
                }
                case ObjectiveFunction::MIN_DVH: {
                    // Tính DVH và xác định liều cho phần trăm thể tích
                    std::vector<double> doses;
                    for (size_t i = 0; i < total_dose.size(); ++i) {
                        for (size_t j = 0; j < total_dose[i].size(); ++j) {
                            for (size_t k = 0; k < total_dose[i][j].size(); ++k) {
                                if (mask[i][j][k] > 0) {
                                    doses.push_back(total_dose[i][j][k]);
                                }
                            }
                        }
                    }
                    
                    if (!doses.empty()) {
                        std::sort(doses.begin(), doses.end());
                        int idx = static_cast<int>(doses.size() * (objective.volume_percent / 100.0));
                        idx = std::min(std::max(0, idx), static_cast<int>(doses.size() - 1));
                        double actual_dose = doses[idx];
                        obj_value = std::max(0.0, objective.dose - actual_dose);
                    }
                    break;
                }
                case ObjectiveFunction::CONFORMITY: {
                    // Mục tiêu: Độ tương thích cao (liều trong PTV cao, ngoài PTV thấp)
                    // Chỉ số đơn giản: tỷ lệ thể tích nhận >= 95% liều mục tiêu nằm trong PTV
                    
                    // Triển khai chỉ số tương thích thực tế (Paddick Conformity Index)
                    // Paddick CI = (TV_PIV)² / (TV × PIV)
                    // TV_PIV: thể tích đích nhận liều kê toa
                    // TV: thể tích đích
                    // PIV: thể tích nhận liều kê toa
                    
                    // Tìm tất cả các voxel nhận ít nhất liều kê toa (PIV)
                    double prescribed_dose = objective.dose;
                    int piv_volume = 0;  // Thể tích nhận liều kê toa
                    int tv_volume = 0;   // Thể tích đích
                    int tv_piv_volume = 0; // Thể tích đích nhận liều kê toa
                    
                    // Tính các thể tích
                    for (size_t i = 0; i < total_dose.size(); ++i) {
                        for (size_t j = 0; j < total_dose[i].size(); ++j) {
                            for (size_t k = 0; k < total_dose[i][j].size(); ++k) {
                                // Kiểm tra xem voxel có nằm trong PTV không
                                bool is_in_target = mask[i][j][k] > 0;
                                
                                // Kiểm tra xem voxel có nhận đủ liều không
                                bool is_in_piv = total_dose[i][j][k] >= prescribed_dose;
                                
                                // Cập nhật các thể tích
                                if (is_in_target) {
                                    tv_volume++;
                                }
                                
                                if (is_in_piv) {
                                    piv_volume++;
                                }
                                
                                if (is_in_target && is_in_piv) {
                                    tv_piv_volume++;
                                }
                            }
                        }
                    }
                    
                    // Tính chỉ số Paddick
                    double paddick_ci = 0.0;
                    if (tv_volume > 0 && piv_volume > 0) {
                        paddick_ci = std::pow(tv_piv_volume, 2) / (static_cast<double>(tv_volume) * piv_volume);
                    }
                    
                    // Mục tiêu là tối đa hóa chỉ số Paddick (gần 1.0)
                    // Chuyển thành bài toán tối thiểu hóa
                    obj_value = std::max(0.0, 1.0 - paddick_ci);
                    break;
                }
                default:
                    std::cerr << "Loại mục tiêu chưa được hỗ trợ" << std::endl;
                    break;
            }
            
            total_objective += objective.weight * obj_value;
        }
        
        return total_objective;
    }
    
    // Tìm cá thể tốt nhất (có độ thích nghi thấp nhất)
    int find_best_individual() {
        int best_idx = 0;
        double best_fitness_val = fitness[0];
        
        for (size_t i = 1; i < fitness.size(); ++i) {
            if (fitness[i] < best_fitness_val) {
                best_fitness_val = fitness[i];
                best_idx = i;
            }
        }
        
        return best_idx;
    }
    
    // Tìm n cá thể tốt nhất
    std::vector<int> find_elite_individuals(int n) {
        std::vector<std::pair<double, int>> fitness_with_idx;
        for (size_t i = 0; i < fitness.size(); ++i) {
            fitness_with_idx.push_back(std::make_pair(fitness[i], i));
        }
        
        std::sort(fitness_with_idx.begin(), fitness_with_idx.end());
        
        std::vector<int> elite_indices;
        for (int i = 0; i < n && i < static_cast<int>(fitness_with_idx.size()); ++i) {
            elite_indices.push_back(fitness_with_idx[i].second);
        }
        
        return elite_indices;
    }
    
    // Chọn cá thể dựa trên độ thích nghi (sử dụng tournament selection)
    std::vector<double> select_individual() {
        std::random_device rd;
        std::mt19937 gen(rd());
        
        // Chọn ngẫu nhiên k cá thể và lấy cá thể tốt nhất
        const int k = 3; // tournament size
        std::vector<int> tournament;
        
        for (int i = 0; i < k; ++i) {
            int idx = std::uniform_int_distribution<int>(0, population.size() - 1)(gen);
            tournament.push_back(idx);
        }
        
        int best_idx = tournament[0];
        double best_fitness_val = fitness[best_idx];
        
        for (size_t i = 1; i < tournament.size(); ++i) {
            int idx = tournament[i];
            if (fitness[idx] < best_fitness_val) {
                best_fitness_val = fitness[idx];
                best_idx = idx;
            }
        }
        
        return population[best_idx];
    }
    
    // Lai ghép hai cá thể để tạo ra hai cá thể con
    std::pair<std::vector<double>, std::vector<double>> crossover(
        const std::vector<double>& parent1, 
        const std::vector<double>& parent2
    ) {
        std::random_device rd;
        std::mt19937 gen(rd());
        
        // Sử dụng lai ghép một điểm
        int crossover_point = std::uniform_int_distribution<int>(1, parent1.size() - 2)(gen);
        
        std::vector<double> child1 = parent1;
        std::vector<double> child2 = parent2;
        
        for (size_t i = crossover_point; i < parent1.size(); ++i) {
            child1[i] = parent2[i];
            child2[i] = parent1[i];
        }
        
        return std::make_pair(child1, child2);
    }
    
    // Đột biến cá thể
    void mutate(std::vector<double>& individual) {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<double> dis(0.0, 1.0);
        
        for (size_t i = 0; i < individual.size(); ++i) {
            if (dis(gen) < mutation_rate) {
                // Thêm một giá trị ngẫu nhiên từ -0.2 đến 0.2
                double delta = dis(gen) * 0.4 - 0.2;
                individual[i] = std::max(0.0, std::min(1.0, individual[i] + delta));
            }
        }
    }
    
    // Chuẩn hóa trọng số để tổng bằng 1
    void normalize_weights(std::vector<double>& weights) {
        double sum = 0.0;
        for (double w : weights) {
            sum += w;
        }
        
        if (sum > 0) {
            for (size_t i = 0; i < weights.size(); ++i) {
                weights[i] /= sum;
            }
        } else {
            // Nếu tổng bằng 0, khởi tạo lại với trọng số đều nhau
            double equal_weight = 1.0 / weights.size();
            for (size_t i = 0; i < weights.size(); ++i) {
                weights[i] = equal_weight;
            }
        }
    }
    
    // Tính toán tổng liều dựa trên trọng số chùm tia
    std::vector<std::vector<std::vector<double>>> calculate_total_dose(const std::vector<double>& weights) {
        auto result = dose_matrix; // Khởi tạo với ma trận liều ban đầu (nếu có)
        
        // Nếu không có ma trận liều ban đầu, khởi tạo ma trận kết quả với giá trị 0
        if (result.empty() && !beam_dose_matrices.empty()) {
            size_t dimX = beam_dose_matrices[0].size();
            size_t dimY = beam_dose_matrices[0][0].size();
            size_t dimZ = beam_dose_matrices[0][0][0].size();
            
            result.resize(dimX, std::vector<std::vector<double>>(dimY, std::vector<double>(dimZ, 0.0)));
        }
        
        // Tích hợp liều từ mỗi chùm tia theo trọng số
        for (size_t b = 0; b < beam_dose_matrices.size() && b < weights.size(); ++b) {
            const auto& beam_dose = beam_dose_matrices[b];
            double weight = weights[b];
            
            for (size_t i = 0; i < result.size(); ++i) {
                for (size_t j = 0; j < result[i].size(); ++j) {
                    for (size_t k = 0; k < result[i][j].size(); ++k) {
                        result[i][j][k] += weight * beam_dose[i][j][k];
                    }
                }
            }
        }
        
        return result;
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

    // Hàm chuyển đổi dữ liệu từ Python sang C++
    void* convert_python_data(void* py_dose_matrix, void* py_structure_masks, 
                             void* py_objectives, void* py_settings) {
        try {
            // Chuyển đổi ma trận liều
            // Giả sử py_dose_matrix là mảng numpy 3D
            // Cần sử dụng Python C API để truy cập dữ liệu
            
            // Tạo ma trận liều C++
            std::vector<std::vector<std::vector<double>>> dose_matrix;
            
            // Chuyển đổi mặt nạ cấu trúc
            std::map<std::string, std::vector<std::vector<std::vector<int>>>> structure_masks;
            
            // Chuyển đổi mục tiêu
            std::vector<ObjectiveFunction> objectives;
            
            // Chuyển đổi thông số
            double learning_rate = 0.01;
            int max_iterations = 100;
            double convergence_threshold = 1e-4;
            
            // Đọc thông số từ py_settings
            // ...
            
            // Tạo đối tượng tối ưu hóa
            GradientOptimizer* optimizer = new GradientOptimizer(
                dose_matrix, structure_masks, learning_rate, max_iterations, convergence_threshold
            );
            
            // Thêm các mục tiêu
            for (const auto& obj : objectives) {
                optimizer->add_objective(obj);
            }
            
            // Khởi tạo trọng số chùm tia
            optimizer->initialize_beam_weights();
            
            return static_cast<void*>(optimizer);
        } catch (const std::exception& e) {
            std::cerr << "Lỗi khi chuyển đổi dữ liệu Python sang C++: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    /**
     * Giải phóng bộ nhớ của đối tượng tối ưu hóa
     * 
     * @param optimizer Con trỏ đến đối tượng GradientOptimizer
     */
    void free_optimizer(void* optimizer) {
        if (optimizer) {
            delete static_cast<GradientOptimizer*>(optimizer);
        }
    }
    
    /**
     * Thực hiện tối ưu hóa
     * 
     * @param optimizer Con trỏ đến đối tượng GradientOptimizer
     * @param py_result Con trỏ đến đối tượng Python để lưu kết quả
     * @return 1 nếu thành công, 0 nếu thất bại
     */
    int run_optimization(void* optimizer, void* py_result) {
        try {
            if (!optimizer) {
                return 0;
            }
            
            GradientOptimizer* opt = static_cast<GradientOptimizer*>(optimizer);
            
            // Tính giá trị mục tiêu ban đầu
            double initial_objective = opt->calculate_objective_function();
            
            // Thực hiện tối ưu hóa
            std::vector<double> weights = opt->optimize();
            
            // Tính giá trị mục tiêu sau tối ưu
            double final_objective = opt->calculate_objective_function();
            
            // Chuyển kết quả về Python
            // Cần sử dụng Python C API để cập nhật py_result
            
            return 1;
        } catch (const std::exception& e) {
            std::cerr << "Lỗi khi thực hiện tối ưu hóa: " << e.what() << std::endl;
            return 0;
        }
    }
}
