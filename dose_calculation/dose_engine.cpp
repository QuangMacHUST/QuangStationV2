#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <memory>
#include <algorithm>
#include <unordered_map>
#include <fstream>
#include <sstream>
#include <iomanip>

// Cấu trúc dữ liệu cho vật liệu
struct Material {
    std::string name;
    double density;                  // g/cm3
    double electron_density_relative; // Tương đối so với nước
    
    Material(const std::string& n, double d, double edr) 
        : name(n), density(d), electron_density_relative(edr) {}
};

// Bảng chuyển đổi HU sang mật độ điện tử
class HUtoEDConverter {
private:
    std::vector<std::pair<int, double>> conversion_table;
    
public:
    HUtoEDConverter() {
        // Giá trị mặc định
        conversion_table = {
            {-1000, 0.001},  // Không khí
            {-950, 0.001},   // Không khí
            {-700, 0.25},    // Phổi
            {-100, 0.9},     // Mỡ
            {0, 1.0},        // Nước
            {50, 1.05},      // Mô mềm
            {300, 1.5},      // Xương
            {1000, 2.0},     // Kim loại
            {3000, 3.0}      // Kim loại cứng
        };
    }
    
    void load_from_file(const std::string& filename) {
        std::ifstream file(filename);
        if (!file.is_open()) {
            std::cerr << "Không thể mở file HU-ED: " << filename << std::endl;
            return;
        }
        
        conversion_table.clear();
        std::string line;
        while (std::getline(file, line)) {
            std::istringstream iss(line);
            int hu;
            double ed;
            if (iss >> hu >> ed) {
                conversion_table.push_back({hu, ed});
            }
        }
        
        // Sắp xếp bảng theo HU tăng dần
        std::sort(conversion_table.begin(), conversion_table.end());
        file.close();
    }
    
    double convert(int hu) const {
        // Nếu HU nhỏ hơn giá trị nhỏ nhất trong bảng
        if (hu <= conversion_table.front().first) {
            return conversion_table.front().second;
        }
        
        // Nếu HU lớn hơn giá trị lớn nhất trong bảng
        if (hu >= conversion_table.back().first) {
            return conversion_table.back().second;
        }
        
        // Nội suy tuyến tính
        for (size_t i = 0; i < conversion_table.size() - 1; ++i) {
            if (hu >= conversion_table[i].first && hu < conversion_table[i + 1].first) {
                double hu1 = conversion_table[i].first;
                double hu2 = conversion_table[i + 1].first;
                double ed1 = conversion_table[i].second;
                double ed2 = conversion_table[i + 1].second;
                
                return ed1 + (ed2 - ed1) * (hu - hu1) / (hu2 - hu1);
            }
        }
        
        // Mặc định trả về mật độ nước
        return 1.0;
    }
};

// Cấu trúc dữ liệu cho beam
struct Beam {
    std::string id;
    std::string type;           // "photon", "electron", "proton"
    double energy;              // MV hoặc MeV
    double gantry_angle;        // độ
    double collimator_angle;    // độ
    double couch_angle;         // độ
    std::vector<std::vector<double>> mlc_positions; // Vị trí MLC (mm) cho từng control point
    std::vector<double> weights;  // Trọng số cho từng control point
    double ssd;                 // Source-Surface Distance (mm)
    std::array<double, 3> isocenter; // Tọa độ tâm (mm)
    
    // Thông số cho VMAT
    bool is_arc;
    double arc_start_angle;
    double arc_stop_angle;
    double arc_direction;       // 1 CW, -1 CCW
    
    // Thông số cho wedge
    bool has_wedge;
    std::string wedge_type;     // "physical", "enhanced", "virtual"
    double wedge_angle;
    double wedge_orientation;
    
    // Constructor
    Beam(const std::string& bid, const std::string& btype, double e) 
        : id(bid), type(btype), energy(e), gantry_angle(0), collimator_angle(0), 
          couch_angle(0), ssd(1000), is_arc(false), 
          arc_start_angle(0), arc_stop_angle(0), arc_direction(1),
          has_wedge(false), wedge_angle(0), wedge_orientation(0) {
        isocenter = {0, 0, 0};
    }
};

// Cấu trúc dữ liệu cho kế hoạch
struct Plan {
    std::string id;
    std::string technique;      // "3DCRT", "IMRT", "VMAT", "SBRT"
    double prescribed_dose;     // Gy
    int fractions;
    std::vector<std::shared_ptr<Beam>> beams;
    
    Plan(const std::string& pid, const std::string& tech, double dose, int frac) 
        : id(pid), technique(tech), prescribed_dose(dose), fractions(frac) {}
};

// Thông số vật lý cho tính toán liều
struct PhysicalParameters {
    double alpha_beta_ratio;    // Tỷ số alpha/beta cho mô (Gy)
    double rbe;                 // Hiệu quả sinh học tương đối
};

// Cấu trúc cho DVH (Dose Volume Histogram)
struct DVH {
    std::string structure_name;
    std::vector<double> dose_bins;  // Giá trị liều (Gy)
    std::vector<double> volume;     // Thể tích tích lũy (%)
    
    // Thông số thống kê liều
    double d_min;   // Liều tối thiểu
    double d_max;   // Liều tối đa
    double d_mean;  // Liều trung bình
    double v95;     // Thể tích nhận 95% liều
    double v100;    // Thể tích nhận 100% liều
    double d95;     // Liều tại 95% thể tích
    double d50;     // Liều tại 50% thể tích
    double d2cc;    // Liều tại 2cc thể tích
    
    DVH(const std::string& name) : structure_name(name), d_min(0), d_max(0), 
          d_mean(0), v95(0), v100(0), d95(0), d50(0), d2cc(0) {}
};

// Lớp cơ sở cho các thuật toán tính liều
class DoseAlgorithm {
public:
    virtual ~DoseAlgorithm() = default;
    
    virtual std::vector<std::vector<std::vector<double>>> calculateDose(
        const std::vector<std::vector<std::vector<int>>>& ct_data,
        const std::array<double, 3>& voxel_size,
        const std::vector<std::vector<std::vector<int>>>& structure_masks,
        const Plan& plan) = 0;
        
    virtual std::string getName() const = 0;
};

// Thuật toán Collapsed Cone Convolution
class CollapsedConeConvolution : public DoseAlgorithm {
private:
    int num_cones;
    double dose_grid_resolution;
    HUtoEDConverter hu_to_ed;
    
public:
    CollapsedConeConvolution(int cones = 24, double resolution = 2.5)
        : num_cones(cones), dose_grid_resolution(resolution) {}
    
    void set_hu_to_ed_conversion_file(const std::string& filename) {
        hu_to_ed.load_from_file(filename);
    }
    
    std::vector<std::vector<std::vector<double>>> calculateDose(
        const std::vector<std::vector<std::vector<int>>>& ct_data,
        const std::array<double, 3>& voxel_size,
        const std::vector<std::vector<std::vector<int>>>& structure_masks,
        const Plan& plan) override {
        
        // Kích thước dữ liệu CT
        size_t depth = ct_data.size();
        size_t height = ct_data[0].size();
        size_t width = ct_data[0][0].size();
        
        // Khởi tạo ma trận liều
        std::vector<std::vector<std::vector<double>>> dose(
            depth, std::vector<std::vector<double>>(
                height, std::vector<double>(width, 0.0)
            )
        );
        
        // Chuyển đổi CT thành mật độ điện tử
        std::vector<std::vector<std::vector<double>>> electron_density(
            depth, std::vector<std::vector<double>>(
                height, std::vector<double>(width, 0.0)
            )
        );
        
        for (size_t z = 0; z < depth; ++z) {
            for (size_t y = 0; y < height; ++y) {
                for (size_t x = 0; x < width; ++x) {
                    // Chuyển đổi HU thành mật độ điện tử tương đối
                    electron_density[z][y][x] = hu_to_ed.convert(ct_data[z][y][x]);
                }
            }
        }
        
        // Tính toán liều cho từng beam
        for (const auto& beam : plan.beams) {
            std::vector<std::vector<std::vector<double>>> beam_dose(
                depth, std::vector<std::vector<double>>(
                    height, std::vector<double>(width, 0.0)
                )
            );
            
            // Tính toán dose kernel
            auto kernel = generate_dose_kernel(beam->energy, beam->type);
            
            // Tính hướng chùm tia dựa trên góc
            auto beam_direction = calculate_beam_direction(
                beam->gantry_angle, beam->couch_angle
            );
            
            if (beam->is_arc) {
                // Tính toán liều cho VMAT với nhiều control points
                int num_control_points = static_cast<int>(
                    std::abs(beam->arc_stop_angle - beam->arc_start_angle) / 2.0
                );
                
                for (int cp = 0; cp < num_control_points; ++cp) {
                    double angle = beam->arc_start_angle + 
                        (beam->arc_stop_angle - beam->arc_start_angle) * cp / 
                        (num_control_points - 1) * beam->arc_direction;
                    
                    // Tính hướng cho control point hiện tại
                    auto cp_direction = calculate_beam_direction(angle, beam->couch_angle);
                    
                    // Lấy vị trí MLC cho control point hiện tại
                    auto mlc_pos = beam->mlc_positions[cp % beam->mlc_positions.size()];
                    
                    // Tính trọng số cho control point hiện tại
                    double weight = beam->weights[cp % beam->weights.size()];
                    
                    // Tính liều từ control point hiện tại
                    calculate_control_point_dose(
                        beam_dose, electron_density, kernel, 
                        cp_direction, beam->isocenter,
                        mlc_pos, voxel_size, weight
                    );
                }
            } else {
                // Tính toán liều cho IMRT hoặc 3DCRT
                for (size_t cp = 0; cp < beam->mlc_positions.size(); ++cp) {
                    auto mlc_pos = beam->mlc_positions[cp];
                    double weight = beam->weights[cp];
                    
                    calculate_control_point_dose(
                        beam_dose, electron_density, kernel, 
                        beam_direction, beam->isocenter,
                        mlc_pos, voxel_size, weight
                    );
                    
                    // Áp dụng wedge nếu có
                    if (beam->has_wedge) {
                        apply_wedge_modulation(
                            beam_dose, beam_direction, beam->isocenter,
                            beam->wedge_angle, beam->wedge_orientation,
                            voxel_size
                        );
                    }
                }
            }
            
            // Cộng liều từ beam vào tổng liều
            for (size_t z = 0; z < depth; ++z) {
                for (size_t y = 0; y < height; ++y) {
                    for (size_t x = 0; x < width; ++x) {
                        dose[z][y][x] += beam_dose[z][y][x];
                    }
                }
            }
        }
        
        // Chuẩn hóa liều theo liều kê toa
        normalize_dose(dose, structure_masks, plan.prescribed_dose);
        
        return dose;
    }
    
    std::string getName() const override {
        return "Collapsed Cone Convolution";
    }
    
private:
    // Chuyển đổi HU thành mật độ điện tử tương đối (đã được thay thế bằng HUtoEDConverter)
    double hounsfield_to_electron_density(int hu) {
        return hu_to_ed.convert(hu);
    }
    
    // Sinh dose kernel dựa trên loại và năng lượng chùm tia
    std::vector<std::vector<std::vector<double>>> generate_dose_kernel(
        double energy, const std::string& beam_type) {
        
        // Kích thước kernel (đơn giản hóa cho ví dụ)
        int kernel_size = 11;
        std::vector<std::vector<std::vector<double>>> kernel(
            kernel_size, std::vector<std::vector<double>>(
                kernel_size, std::vector<double>(kernel_size, 0.0)
            )
        );
        
        int center = kernel_size / 2;
        
        // Tham số cho kernel dựa trên loại và năng lượng chùm tia
        double sigma = 0;
        if (beam_type == "photon") {
            sigma = 0.5 + energy * 0.1;  // Đơn giản hóa cho ví dụ
        } else if (beam_type == "electron") {
            sigma = 0.3 + energy * 0.05;
        } else if (beam_type == "proton") {
            // Cho proton, tạo kernel Bragg peak
            double range = energy * 0.3; // Đơn giản hóa: phạm vi (cm) = 0.3 * E(MeV)
            double sigma_r = 0.03 * range;
            
            for (int z = 0; z < kernel_size; ++z) {
                for (int y = 0; y < kernel_size; ++y) {
                    for (int x = 0; x < kernel_size; ++x) {
                        double r2 = pow(x - center, 2) + pow(y - center, 2);
                        double depth = z - center;
                        
                        // Mô phỏng đường cong Bragg đơn giản
                        if (depth <= range) {
                            double bragg = 1.0 + 5.0 * exp(-20.0 * pow(depth - range, 2));
                            kernel[z][y][x] = bragg * exp(-r2 / (2 * sigma_r * sigma_r));
                        }
                    }
                }
            }
            
            // Chuẩn hóa kernel
            double sum = 0.0;
            for (int z = 0; z < kernel_size; ++z) {
                for (int y = 0; y < kernel_size; ++y) {
                    for (int x = 0; x < kernel_size; ++x) {
                        sum += kernel[z][y][x];
                    }
                }
            }
            
            if (sum > 0) {
                for (int z = 0; z < kernel_size; ++z) {
                    for (int y = 0; y < kernel_size; ++y) {
                        for (int x = 0; x < kernel_size; ++x) {
                            kernel[z][y][x] /= sum;
                        }
                    }
                }
            }
            
            return kernel;
        }
        
        // Tính toán kernel cho photon/electron
        double sum = 0.0;
        for (int z = 0; z < kernel_size; ++z) {
            for (int y = 0; y < kernel_size; ++y) {
                for (int x = 0; x < kernel_size; ++x) {
                    double r2 = pow(x - center, 2) + pow(y - center, 2) + pow(z - center, 2);
                    kernel[z][y][x] = exp(-r2 / (2 * sigma * sigma));
                    sum += kernel[z][y][x];
                }
            }
        }
        
        // Chuẩn hóa kernel
        if (sum > 0) {
            for (int z = 0; z < kernel_size; ++z) {
                for (int y = 0; y < kernel_size; ++y) {
                    for (int x = 0; x < kernel_size; ++x) {
                        kernel[z][y][x] /= sum;
                    }
                }
            }
        }
        
        return kernel;
    }
    
    // Tính hướng chùm tia dựa trên góc gantry và couch
    std::array<double, 3> calculate_beam_direction(double gantry_angle, double couch_angle) {
        double gantry_rad = gantry_angle * M_PI / 180.0;
        double couch_rad = couch_angle * M_PI / 180.0;
        
        std::array<double, 3> direction;
        direction[0] = sin(gantry_rad) * cos(couch_rad);
        direction[1] = cos(gantry_rad);
        direction[2] = sin(gantry_rad) * sin(couch_rad);
        
        // Chuẩn hóa vector hướng
        double magnitude = sqrt(direction[0] * direction[0] + 
                               direction[1] * direction[1] + 
                               direction[2] * direction[2]);
        
        if (magnitude > 0) {
            direction[0] /= magnitude;
            direction[1] /= magnitude;
            direction[2] /= magnitude;
        }
        
        return direction;
    }
    
    // Áp dụng hiệu ứng wedge
    void apply_wedge_modulation(
        std::vector<std::vector<std::vector<double>>>& beam_dose,
        const std::array<double, 3>& beam_direction,
        const std::array<double, 3>& isocenter,
        double wedge_angle,
        double wedge_orientation,
        const std::array<double, 3>& voxel_size
    ) {
        // Chuyển đổi góc wedge từ độ sang radian
        double wedge_rad = wedge_angle * M_PI / 180.0;
        double orientation_rad = wedge_orientation * M_PI / 180.0;
        
        // Tính hướng wedge
        std::array<double, 3> wedge_direction = {
            cos(orientation_rad),
            0,
            sin(orientation_rad)
        };
        
        // Kích thước dữ liệu
        size_t depth = beam_dose.size();
        size_t height = beam_dose[0].size();
        size_t width = beam_dose[0][0].size();
        
        // Tính hệ số wedge cho từng voxel
        for (size_t z = 0; z < depth; ++z) {
            for (size_t y = 0; y < height; ++y) {
                for (size_t x = 0; x < width; ++x) {
                    // Tính tọa độ voxel trong không gian thực (mm)
                    double voxel_x = x * voxel_size[0];
                    double voxel_y = y * voxel_size[1];
                    double voxel_z = z * voxel_size[2];
                    
                    // Tính vector từ isocenter đến voxel
                    double dx = voxel_x - isocenter[0];
                    double dy = voxel_y - isocenter[1];
                    double dz = voxel_z - isocenter[2];
                    
                    // Chiếu vector này lên hướng wedge
                    double projection = dx * wedge_direction[0] + 
                                       dy * wedge_direction[1] + 
                                       dz * wedge_direction[2];
                    
                    // Tính hệ số wedge (đơn giản hóa)
                    double max_distance = 100.0; // mm
                    double normalized_position = projection / max_distance;
                    
                    // Hệ số wedge từ 1.0 đến cos(wedge_angle)
                    double wedge_factor = 1.0 - (1.0 - cos(wedge_rad)) * normalized_position;
                    
                    // Đảm bảo hệ số wedge không âm
                    wedge_factor = std::max(0.1, wedge_factor);
                    
                    // Áp dụng hệ số wedge
                    beam_dose[z][y][x] *= wedge_factor;
                }
            }
        }
    }
    
    // Tính liều từ một control point
    void calculate_control_point_dose(
        std::vector<std::vector<std::vector<double>>>& beam_dose,
        const std::vector<std::vector<std::vector<double>>>& electron_density,
        const std::vector<std::vector<std::vector<double>>>& kernel,
        const std::array<double, 3>& beam_direction,
        const std::array<double, 3>& isocenter,
        const std::vector<double>& mlc_positions,
        const std::array<double, 3>& voxel_size,
        double weight
    ) {
        // Kích thước dữ liệu
        size_t depth = electron_density.size();
        size_t height = electron_density[0].size();
        size_t width = electron_density[0][0].size();
        
        // Kích thước kernel
        size_t kernel_size = kernel.size();
        int kernel_center = kernel_size / 2;
        
        // Tính toán liều cho từng voxel
        #pragma omp parallel for collapse(3)
        for (size_t z = 0; z < depth; ++z) {
            for (size_t y = 0; y < height; ++y) {
                for (size_t x = 0; x < width; ++x) {
                    // Kiểm tra xem voxel có trong trường chiếu không (đơn giản hóa)
                    if (is_inside_field(x, y, z, mlc_positions, beam_direction, isocenter, voxel_size)) {
                        // Tính khoảng cách từ voxel đến isocenter dọc theo hướng chùm tia
                        double distance = calculate_distance(
                            x, y, z, isocenter, beam_direction, voxel_size
                        );
                        
                        // Tính tổng liều từ kernel
                        double voxel_dose = 0.0;
                        
                        // Giới hạn duyệt kernel để tối ưu hiệu suất
                        int half_kernel = kernel_center / 2;
                        
                        for (int kz = kernel_center - half_kernel; kz <= kernel_center + half_kernel; ++kz) {
                            for (int ky = kernel_center - half_kernel; ky <= kernel_center + half_kernel; ++ky) {
                                for (int kx = kernel_center - half_kernel; kx <= kernel_center + half_kernel; ++kx) {
                                    // Tính vị trí voxel mới
                                    int nx = x + (kx - kernel_center);
                                    int ny = y + (ky - kernel_center);
                                    int nz = z + (kz - kernel_center);
                                    
                                    // Kiểm tra biên
                                    if (nx >= 0 && nx < width && ny >= 0 && ny < height && nz >= 0 && nz < depth) {
                                        voxel_dose += kernel[kz][ky][kx] * electron_density[nz][ny][nx];
                                    }
                                }
                            }
                        }
                        
                        // Áp dụng hiệu ứng giảm liều theo khoảng cách (inverse square law)
                        // và hiệu ứng suy giảm theo độ sâu
                        double source_distance = 1000.0; // SSD mặc định (mm)
                        double depth_factor = exp(-0.005 * distance); // Đơn giản hóa
                        double inverse_square = pow(source_distance / (source_distance + distance), 2);
                        
                        voxel_dose *= depth_factor * inverse_square * weight;
                        
                        // Thêm vào beam dose
                        beam_dose[z][y][x] += voxel_dose;
                    }
                }
            }
        }
    }
    
    // Kiểm tra voxel có trong trường chiếu không
    bool is_inside_field(
        size_t x, size_t y, size_t z,
        const std::vector<double>& mlc_positions,
        const std::array<double, 3>& beam_direction,
        const std::array<double, 3>& isocenter,
        const std::array<double, 3>& voxel_size
    ) {
        // Tính tọa độ voxel trong không gian thực (mm)
        double voxel_x = x * voxel_size[0];
        double voxel_y = y * voxel_size[1];
        double voxel_z = z * voxel_size[2];
        
        // Tính vector từ isocenter đến voxel
        double dx = voxel_x - isocenter[0];
        double dy = voxel_y - isocenter[1];
        double dz = voxel_z - isocenter[2];
        
        // Tính khoảng cách dọc theo hướng chùm tia
        double proj = dx * beam_direction[0] + dy * beam_direction[1] + dz * beam_direction[2];
        
        // Nếu voxel nằm sau nguồn, bỏ qua
        if (proj < 0) {
            return false;
        }
        
        // Tính tọa độ của voxel trên mặt phẳng vuông góc với chùm tia
        // (đơn giản hóa)
        double field_x = dx - proj * beam_direction[0];
        double field_y = dy - proj * beam_direction[1];
        
        // Tính hướng vuông góc với chùm tia
        std::array<double, 3> perp_x = {0, 0, 0};
        std::array<double, 3> perp_y = {0, 0, 0};
        
        // Tính vector vuông góc thứ nhất (nằm trên mặt phẳng ngang)
        perp_x[0] = -beam_direction[2];
        perp_x[2] = beam_direction[0];
        double magnitude_x = sqrt(perp_x[0] * perp_x[0] + perp_x[2] * perp_x[2]);
        
        if (magnitude_x > 0) {
            perp_x[0] /= magnitude_x;
            perp_x[2] /= magnitude_x;
        } else {
            // Trường hợp chùm tia nằm dọc trục Y
            perp_x[0] = 1.0;
            perp_x[2] = 0.0;
        }
        
        // Tính vector vuông góc thứ hai (vuông góc với cả beam_direction và perp_x)
        perp_y[0] = beam_direction[1] * perp_x[2] - beam_direction[2] * perp_x[1];
        perp_y[1] = beam_direction[2] * perp_x[0] - beam_direction[0] * perp_x[2];
        perp_y[2] = beam_direction[0] * perp_x[1] - beam_direction[1] * perp_