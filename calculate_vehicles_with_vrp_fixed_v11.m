% calculate_vehicles_with_vrp_fixed_v11.m
% Fiziksel engelli öğrenciler için araç sayısı hesaplama
% Veri.xlsx dosyasından Time, Pick ve Drop verilerini okur
% Kullanıcı, zaman dilimi ve rota optimizasyon algoritması seçer
% Kapasite: Sw <= 4, So <= 5 (karışık kombinasyonlar mümkün)
% Tur süresi üst sınırı kullanıcı tarafından girilir (varsayılan: 120 dk)
% Öğrenci sayısı, veri dosyasındaki 1 işaretlemelerine göre dinamik olarak belirlenir

% Excel dosyasını oku
filename = 'Veri.xlsx';

% Time sayfasını oku
time_sheet = readmatrix(filename, 'Sheet', 'Time', 'Range', 'C4:AE32');
locations = readcell(filename, 'Sheet', 'Time', 'Range', 'B4:B32'); % Konum isimleri
coords_cell = readcell(filename, 'Sheet', 'Time', 'Range', 'C2:AE2'); % Koordinatlar

% time_sheet'te NaN, Inf veya negatif değerleri işle
if any(isnan(time_sheet(:)) | isinf(time_sheet(:)) | time_sheet(:) < 0)
    warning('time_sheet matrisinde NaN, Inf veya negatif değerler bulundu. Bunlar 0 ile değiştiriliyor.');
    time_sheet(isnan(time_sheet) | isinf(time_sheet) | time_sheet < 0) = 0; % Negatif, NaN ve Inf 0 ile değiştirilir
end
% Diagonalde 0 olduğundan emin ol
for i = 1:size(time_sheet, 1)
    time_sheet(i, i) = 0;
end

% Koordinatları ondalık dereceye çevir
coords = zeros(length(coords_cell), 2);
for i = 1:length(coords_cell)
    if ~ismissing(coords_cell{i})
        [lat, lon] = dms2degrees(coords_cell{i});
        coords(i, 1) = lat;
        coords(i, 2) = lon;
    end
end

% Pick ve Drop sayfalarını oku
pick_data = readtable(filename, 'Sheet', 'Pick');
drop_data = readtable(filename, 'Sheet', 'Drop');

% Pick ve Drop sütun isimlerini al (zaman dilimleri)
pick_columns = pick_data.Properties.VariableNames(3:end); % İlk iki sütun hariç
drop_columns = drop_data.Properties.VariableNames(3:end);
all_timeslots = [pick_columns, drop_columns];

% Kullanıcıya zaman dilimlerini göster ve seçim yaptır
fprintf('Mevcut zaman dilimleri:\n');
for i = 1:length(all_timeslots)
    fprintf('%d: %s\n', i, all_timeslots{i});
end
selected_idx = input('Hesaplama için zaman dilimi numarasını seçin: ');
selected_timeslot = all_timeslots{selected_idx};

% Geçerli öğrenci listesi (Sw1-Sw9, So1-So19)
valid_students = [arrayfun(@(x) sprintf('Sw%d', x), 1:9, 'UniformOutput', false), ...
                  arrayfun(@(x) sprintf('So%d', x), 1:19, 'UniformOutput', false)];

% Seçilen zaman diliminden öğrencileri al
if contains(selected_timeslot, 'Pick')
    students = pick_data.Ogrenci(pick_data.(selected_timeslot) == 1);
elseif contains(selected_timeslot, 'Drop')
    students = drop_data.Ogrenci(drop_data.(selected_timeslot) == 1);
else
    error('Geçersiz zaman dilimi seçimi.');
end

% Öğrencileri geçerli öğrenci listesiyle filtrele
invalid_students = setdiff(students, valid_students);
if ~isempty(invalid_students)
    warning('Geçersiz öğrenciler bulundu: %s. Bu öğrenciler yoksayılacak.', strjoin(invalid_students, ', '));
    students = intersect(students, valid_students, 'stable');
end

% Öğrenci türlerini ve sayısını belirle
sw_count = sum(contains(students, 'Sw')); % Sw öğrenci sayısı
so_count = sum(contains(students, 'So')); % So öğrenci sayısı
fprintf('Sw öğrenci sayısı: %d, So öğrenci sayısı: %d\n', sw_count, so_count);

% Öğrenci sayısı kontrolü
if isempty(students)
    error('Seçilen zaman diliminde geçerli öğrenci bulunamadı.');
end

% Kapasite sınırları
sw_capacity = 4;
so_capacity = 5;

% İlk araç sayısı tahmini
num_vehicles = max(ceil(sw_count / sw_capacity), ceil(so_count / so_capacity));
fprintf('Başlangıç araç sayısı: %d\n', num_vehicles);

% Kullanıcıdan tur süresi üst sınırı al
max_tour_time = input('Tur süresi üst sınırı (dakika, varsayılan 120): ');
if isempty(max_tour_time)
    max_tour_time = 120; % Varsayılan değer
end

% Rota optimizasyon algoritması seçimi
fprintf('Rota optimizasyon algoritmaları:\n');
fprintf('1: Nearest Neighbor (Hızlı, sezgisel)\n');
fprintf('2: MATLAB Optimization Toolbox - TSP (Daha iyi optimizasyon, lisans gerekir)\n');
fprintf('3: Google OR-Tools VRP (Güçlü, Python entegrasyonu gerekir)\n');
opt_method = input('Rota optimizasyon algoritması numarasını seçin (1-3): ');

% Öğrenci indislerini bul
student_indices = zeros(1, length(students));
for i = 1:length(students)
    idx = find(strcmp(locations, students{i}));
    if isempty(idx)
        error('Öğrenci %s konumlar listesinde bulunamadı.', students{i});
    end
    student_indices(i) = idx;
end

% Öğrenci türlerini belirle (Sw: 1, So: 2)
student_types = zeros(1, length(students));
for i = 1:length(students)
    if contains(students{i}, 'Sw')
        student_types(i) = 1;
    else
        student_types(i) = 2;
    end
end

% Kapasite ve süre için veriler
sw_counts = zeros(size(time_sheet, 1), 1);
so_counts = zeros(size(time_sheet, 1), 1);
for i = 1:length(student_indices)
    if student_types(i) == 1
        sw_counts(student_indices(i)) = 1;
    else
        so_counts(student_indices(i)) = 1;
    end
end

% Google OR-Tools için Python entegrasyonu kontrolü
if opt_method == 3
    try
        pyenv; % Python entegrasyonunu kontrol et
    catch
        error('Python entegrasyonu bulunamadı. Lütfen Python ve OR-Tools kurun: https://developers.google.com/optimization/install');
    end
end

% K-means ile gruplama veya VRP
if opt_method == 3
    % Google OR-Tools VRP
    py_data = py.numpy.array(time_sheet);
    py_sw_counts = py.numpy.array(sw_counts);
    py_so_counts = py.numpy.array(so_counts);
    py_num_vehicles = py.int64(num_vehicles);
    py_sw_capacity = py.int64(sw_capacity);
    py_so_capacity = py.int64(so_capacity);
    py_max_tour_time = py.int64(max_tour_time);
    
    try
        result = pyrunfile('vrp.py', {'routes', 'total_time'}, ...
            distance_matrix=py_data, num_vehicles=py_num_vehicles, ...
            sw_counts=py_sw_counts, so_counts=py_so_counts, ...
            sw_capacity=py_sw_capacity, so_capacity=py_so_capacity, ...
            max_tour_time=py_max_tour_time);
        routes = cell(result.routes);
        total_time = double(result.total_time);
        clusters = cell(num_vehicles, 1);
        tour_times = zeros(num_vehicles, 1);
        for v = 1:num_vehicles
            route = routes{v};
            clusters{v} = students(ismember(student_indices, route(2:end-1)));
            tour_times(v) = sum(time_sheet(route(1:end-1), route(2:end)));
        end
    catch
        error('OR-Tools hatası. Python ve OR-Tools kurulumunu kontrol edin.');
    end
else
    % K-means ile gruplama
    while true
        if isempty(student_indices)
            fprintf('Seçilen zaman diliminde öğrenci yok.\n');
            num_vehicles = 0;
            clusters = {};
            tour_times = [];
            break;
        end
        % K-means ile kümeleme
        try
            [cluster_idx, ~] = kmeans(coords(student_indices, :), num_vehicles, 'Distance', 'cityblock', 'MaxIter', 100, 'Replicates', 10);
        catch
            error('K-means kümeleme hatası. Koordinat verilerini kontrol edin.');
        end
        if length(cluster_idx) ~= length(student_indices)
            error('cluster_idx boyutu (%d) öğrenci sayısı (%d) ile uyuşmuyor.', length(cluster_idx), length(student_indices));
        end

        % Her kümenin kapasite ve süre kontrolü
        valid = true;
        tour_times = zeros(num_vehicles, 1);
        clusters = cell(num_vehicles, 1);
        for v = 1:num_vehicles
            cluster_students = student_indices(cluster_idx == v);
            cluster_types = student_types(cluster_idx == v);
            
            % Kapasite kontrolü
            cluster_sw_count = sum(cluster_types == 1);
            cluster_so_count = sum(cluster_types == 2);
            if cluster_sw_count > sw_capacity || cluster_so_count > so_capacity
                valid = false;
                break;
            end
            
            % Rota süresi hesaplama
            if isempty(cluster_students)
                tour_times(v) = 0;
                clusters{v} = {};
                continue;
            end
            
            if opt_method == 1
                [route, tour_time] = nearest_neighbor_route(time_sheet, [1, cluster_students, 1]);
            elseif opt_method == 2
                [route, tour_time] = tsp_route(time_sheet, [1, cluster_students, 1]);
            end
            if isnan(tour_time) || isinf(tour_time)
                warning('Küme %d için NaN veya Inf rota süresi. Nearest Neighbor deneniyor.', v);
                [route, tour_time] = nearest_neighbor_route(time_sheet, [1, cluster_students, 1]);
            end
            tour_times(v) = tour_time;
            clusters{v} = students(cluster_idx == v);
            
            if tour_time > max_tour_time
                valid = false;
                break;
            end
        end
        
        % Tek öğrenci kümelerini kontrol et ve gerekirse araç sayısını artır
        if valid
            single_student_clusters = sum(cellfun(@length, clusters) == 1);
            if single_student_clusters > num_vehicles / 2
                valid = false; % Çok fazla tek öğrenci kümesi, suboptimal
            end
        end
        
        if valid
            break;
        end
        
        num_vehicles = num_vehicles + 1;
        fprintf('Tur süresi, kapasite veya çok fazla tek öğrenci kümesi, araç sayısı artırıldı: %d\n', num_vehicles);
    end
end

% Sonuçları raporla
fprintf('\nSeçilen zaman dilimi: %s\n', selected_timeslot);
fprintf('Seçilen optimizasyon yöntemi: %d\n', opt_method);
fprintf('Gerekli araç sayısı: %d\n', num_vehicles);
for v = 1:num_vehicles
    fprintf('Araç %d:\n', v);
    fprintf('  Öğrenciler: %s\n', strjoin(clusters{v}, ', '));
    fprintf('  Rota süresi: %.2f dakika\n', tour_times(v));
end

% Yardımcı fonksiyon: DMS formatındaki koordinatları ondalık dereceye çevir
function [lat, lon] = dms2degrees(dms_str)
    parts = split(dms_str, {'°', '''', '"'});
    degrees = str2double(parts{1});
    minutes = str2double(parts{2});
    seconds = str2double(parts{3});
    direction = parts{4};
    
    decimal = degrees + minutes/60 + seconds/3600;
    if contains(direction, 'S') || contains(direction, 'W')
        decimal = -decimal;
    end
    
    if contains(dms_str, 'N') || contains(dms_str, 'S')
        lat = decimal;
        lon = 0;
    else
        lat = 0;
        lon = decimal;
    end
end

% Yardımcı fonksiyon: Nearest Neighbor rota optimizasyonu
function [route, tour_time] = nearest_neighbor_route(time_data, nodes)
    n = length(nodes);
    route = zeros(1, n);
    visited = false(1, n);
    route(1) = 1; % D.Kampus
    visited(1) = true;
    tour_time = 0;
    
    for i = 2:n
        current = route(i-1);
        min_dist = inf;
        next_node = 0;
        for j = 1:n
            if ~visited(j) && time_data(current, j) < min_dist
                min_dist = time_data(current, j);
                next_node = j;
            end
        end
        if next_node == 0
            warning('Geçerli bir sonraki düğüm bulunamadı, rota kesildi.');
            tour_time = inf;
            return;
        end
        route(i) = next_node;
        visited(next_node) = true;
        tour_time = tour_time + min_dist;
    end
    tour_time = tour_time + time_data(route(n), 1);
    if isnan(tour_time) || isinf(tour_time)
        tour_time = inf;
    end
end

% Yardımcı fonksiyon: MATLAB TSP optimizasyonu
function [route, tour_time] = tsp_route(time_data, nodes)
    n = length(nodes);
    if n <= 3 % Küçük kümeler için özel durum
        route = nodes;
        if n == 1
            tour_time = 0; % Sadece D.Kampus
        elseif n == 2
            tour_time = time_data(nodes(1), nodes(2)) + time_data(nodes(2), nodes(1)); % D.Kampus -> Öğrenci -> D.Kampus
        else
            % D.Kampus -> Öğrenci1 -> Öğrenci2 -> D.Kampus
            tour_time = time_data(nodes(1), nodes(2)) + time_data(nodes(2), nodes(3)) + time_data(nodes(3), nodes(1));
        end
        if isnan(tour_time) || isinf(tour_time)
            warning('Küçük küme için NaN veya Inf rota süresi, Nearest Neighbor deneniyor.');
            [route, tour_time] = nearest_neighbor_route(time_data, nodes);
        end
        return;
    end
    
    % TSP için ikili değişkenler: x(i,j) = 1 ise i'den j'ye gidilir
    num_vars = (n-1) * (n-1); % Her düğüm için (n-1) olası hedef (kendi dahil değil)
    f = zeros(num_vars, 1);
    edge_map = zeros(n, n); % Kenarları takip etmek için
    idx = 1;
    for i = 2:n
        for j = 2:n
            if i ~= j
                f(idx) = time_data(nodes(i), nodes(j));
                edge_map(i, j) = idx;
                idx = idx + 1;
            end
        end
    end
    
    % Kısıtlamalar: Her düğümden bir çıkış, her düğüme bir giriş
    Aeq = zeros(2*(n-1), num_vars);
    beq = ones(2*(n-1), 1);
    row = 1;
    for i = 2:n
        for j = 2:n
            for k = 2:n
                if j ~= k && edge_map(j, k) > 0
                    if k == i
                        Aeq(row, edge_map(j, k)) = 1; % Çıkış
                    end
                end
            end
        end
        row = row + 1;
    end
    for j = 2:n
        for i = 2:n
            for k = 2:n
                if i ~= k && edge_map(i, k) > 0
                    if i == j
                        Aeq(row, edge_map(i, k)) = 1; % Giriş
                    end
                end
            end
        end
        row = row + 1;
    end
    
    % Alt döngü engelleme (Miller-Tucker-Zemlin)
    A = zeros((n-1)*(n-2), num_vars);
    b = (n-2)*ones((n-1)*(n-2), 1);
    row = 1;
    for i = 2:n
        for j = 2:n
            if i ~= j && edge_map(i, j) > 0
                A(row, edge_map(i, j)) = 1;
                row = row + 1;
            end
        end
    end
    
    % Optimizasyon
    intcon = 1:num_vars;
    lb = zeros(num_vars, 1);
    ub = ones(num_vars, 1);
    opts = optimoptions('intlinprog', 'Display', 'off');
    try
        x = intlinprog(f, intcon, A, b, Aeq, beq, lb, ub, opts);
        if isempty(x)
            warning('intlinprog çözüm bulamadı, Nearest Neighbor kullanılıyor.');
            [route, tour_time] = nearest_neighbor_route(time_data, nodes);
            return;
        end
    catch
        warning('intlinprog başarısız oldu, Nearest Neighbor kullanılıyor.');
        [route, tour_time] = nearest_neighbor_route(time_data, nodes);
        return;
    end
    
    % Rotayı oluştur
    route = [nodes(1)]; % D.Kampus başlangıç
    current = 1;
    visited = false(1, n);
    visited(1) = true;
    for i = 1:n-1
        found = false;
        for j = 2:n
            for k = 2:n
                if j ~= k && ~visited(k) && edge_map(j, k) > 0
                    if x(edge_map(j, k)) > 0.5
                        route = [route, nodes(k)];
                        visited(k) = true;
                        current = k;
                        found = true;
                        break;
                    end
                end
            end
            if found
                break;
            end
        end
        if ~found
            warning('Rota oluşturulamadı, Nearest Neighbor kullanılıyor.');
            [route, tour_time] = nearest_neighbor_route(time_data, nodes);
            return;
        end
    end
    route = [route, nodes(1)]; % D.Kampus dönüş
    tour_time = 0;
    for i = 1:length(route)-1
        tour_time = tour_time + time_data(route(i), route(i+1));
    end
    if isnan(tour_time) || isinf(tour_time)
        warning('TSP rota süresi NaN veya Inf, Nearest Neighbor deneniyor.');
        [route, tour_time] = nearest_neighbor_route(time_data, nodes);
    end
end