#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <memory>
#include <algorithm>
#include <unordered_map>

// Cấu trúc dữ liệu cho vật liệu
struct Material {
    std::string name;
    double density;                  // g/cm3
    double electron_density_relative; // Tương đối so với nước
    
    Material(const std::string& n, double d, double edr) 
        : name(n), density(d), electron_density_relative(edr) {}
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
    
    // Constructor
    Beam(const std::string& bid, const std::string& btype, double e) 
        : id(bid), type(btype), energy(e), gantry_angle(0), collimator_angle(0), 
          couch_angle(0), ssd(1000), is_arc(false), 
          arc_start_angle(0), arc_stop_angle(0), arc_direction(1) {
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
    
public:
    CollapsedConeConvolution(int cones = 24, double resolution = 2.5)
        : num_cones(cones), dose_grid_resolution(resolution) {}
    
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
                    electron_density[z][y][x] = hounsfield_to_electron_density(ct_data[z][y][x]);
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
                        (num_control_points - 1);
                    
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
    // Chuyển đổi HU thành mật độ điện tử tương đối
    double hounsfield_to_electron_density(int hu) {
        if (hu < -950) return 0.001;      // Không khí
        else if (hu < -700) return 0.25;  // Phổi
        else if (hu < -100) return 0.9;   // Mỡ
        else if (hu < 50) return 1.0;     // Nước
        else if (hu < 300) return 1.05;   // Mô mềm
        else if (hu < 1000) return 1.5;   // Xương
        else return 2.0;                  // Kim loại
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
            sigma = 0.2 + energy * 0.02;
        }
        
        // Tính toán kernel
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
        for (int z = 0; z < kernel_size; ++z) {
            for (int y = 0; y < kernel_size; ++y) {
                for (int x = 0; x < kernel_size; ++x) {
                    kernel[z][y][x] /= sum;
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
        
        return direction;
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
                        
                        for (size_t kz = 0; kz < kernel_size; ++kz) {
                            for (size_t ky = 0; ky < kernel_size; ++ky) {
                                for (size_t kx = 0; kx < kernel_size; ++kx) {
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
        // Đơn giản hóa: Kiểm tra xem voxel có nằm trong field size không
        // Field size được xác định bởi MLC
        
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
        
        // Tính tọa độ của voxel trên mặt phẳng vuông góc với chùm tia
        // (đơn giản hóa)
        double field_x = dx - proj * beam_direction[0];
        double field_y = dy - proj * beam_direction[1];
        
        // Kích thước field từ MLC (đơn giản hóa)
        double max_x = *std::max_element(mlc_positions.begin(), mlc_positions.end());
        double min_x = *std::min_element(mlc_positions.begin(), mlc_positions.end());
        
        // Kiểm tra xem voxel có nằm trong field không
        return (field_x >= min_x && field_x <= max_x && std::abs(field_y) <= 100.0);
    }
    
    // Tính khoảng cách từ voxel đến isocenter dọc theo hướng chùm tia
    double calculate_distance(
        size_t x, size_t y, size_t z,
        const std::array<double, 3>& isocenter,
        const std::array<double, 3>& beam_direction,
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
        return std::abs(dx * beam_direction[0] + dy * beam_direction[1] + dz * beam_direction[2]);
    }
    
    // Chuẩn hóa liều theo liều kê toa
    void normalize_dose(
        std::vector<std::vector<std::vector<double>>>& dose,
        const std::vector<std::vector<std::vector<int>>>& structure_masks,
        double prescribed_dose
    ) {
        // Tìm PTV mask
        auto ptv_mask = find_ptv_mask(structure_masks);
        
        // Tìm giá trị liều lớn nhất trong PTV
        double max_dose_in_ptv = 0.0;
        int ptv_voxel_count = 0;
        
        for (size_t z = 0; z < dose.size(); ++z) {
            for (size_t y = 0; y < dose[0].size(); ++y) {
                for (size_t x = 0; x < dose[0][0].size(); ++x) {
                    if (ptv_mask[z][y][x] > 0) {
                        max_dose_in_ptv = std::max(max_dose_in_ptv, dose[z][y][x]);
                        ptv_voxel_count++;
                    }
                }
            }
        }
        
        if (ptv_voxel_count == 0 || max_dose_in_ptv == 0.0) {
            std::cerr << "Không thể chuẩn hóa liều: Không tìm thấy PTV hoặc liều trong PTV là 0" << std::endl;
            return;
        }
        
        // Hệ số chuẩn hóa
        double normalization_factor = prescribed_dose / max_dose_in_ptv;
        
        // Chuẩn hóa liều
        for (size_t z = 0; z < dose.size(); ++z) {
            for (size_t y = 0; y < dose[0].size(); ++y) {
                for (size_t x = 0; x < dose[0][0].size(); ++x) {
                    dose[z][y][x] *= normalization_factor;
                }
            }
        }
    }
    
    // Tìm PTV mask từ danh sách structure masks
    std::vector<std::vector<std::vector<int>>> find_ptv_mask(
        const std::vector<std::vector<std::vector<int>>>& structure_masks) {
        
        for (const auto& mask : structure_masks) {
            // Giả sử PTV mask có giá trị lớn nhất trong mask
            if (*std::max_element(mask[0][0].begin(), mask[0][0].end()) > 0) {
                return mask;
            }
        }
        
        // Trả về mask rỗng nếu không tìm thấy
        return std::vector<std::vector<std::vector<int>>>(
            structure_masks.size(), std::vector<std::vector<int>>(
                structure_masks[0].size(), std::vector<int>(
                    structure_masks[0][0].size(), 0
                )
            )
        );
    }
};