document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const getBtn = document.getElementById('get-location-btn');
    const btnText = getBtn.querySelector('.btn-text');
    const btnIcon = getBtn.querySelector('.btn-icon');
    
    const startWalkBtn = document.getElementById('start-walk-btn');
    const endWalkBtn = document.getElementById('end-walk-btn');
    const statsPanel = document.getElementById('stats-panel');
    const walkTime = document.getElementById('walk-time');
    const walkDistance = document.getElementById('walk-distance');
    
    const summaryOverlay = document.getElementById('summary-overlay');
    const summaryTime = document.getElementById('summary-time');
    const summaryDistance = document.getElementById('summary-distance');
    const closeSummaryBtn = document.getElementById('close-summary-btn');
    
    const radarContainer = document.getElementById('radar-container');
    const locationCard = document.getElementById('location-card');
    const gpsStatusBadge = document.getElementById('gps-status');
    
    // Result Fields
    const valLatitude = document.getElementById('val-latitude');
    const valLongitude = document.getElementById('val-longitude');
    const valAccuracy = document.getElementById('val-accuracy');
    const valAccuracyUnit = document.getElementById('val-accuracy-unit');
    const valTimestamp = document.getElementById('val-timestamp');
    
    // Custom Toast Elements
    const toastOverlay = document.getElementById('toast-overlay');
    const toastTitle = document.getElementById('toast-title');
    const toastMessage = document.getElementById('toast-message');
    const toastIcon = document.getElementById('toast-icon');
    const toastCloseBtn = document.getElementById('toast-close-btn');

    // Camera & Photo Preview Elements
    const takePhotoBtn = document.getElementById('take-photo-btn');
    const cameraInput = document.getElementById('camera-input');
    const photoOverlay = document.getElementById('photo-overlay');
    const photoPreviewImg = document.getElementById('photo-preview-img');
    const photoCloseBtn = document.getElementById('photo-close-btn');
    const photoCaption = document.getElementById('photo-caption');

    // --- Leaflet Map State & Initialization ---
    let map;
    let marker;
    let polyline = null;
    let walkPath = [];
    
    // Camera & Location State
    let currentLocation = null;
    let capturedPhotos = [];
    let photoMarkers = [];
    let watchId = null;
    let totalDistance = 0;
    let lastPosition = null;
    
    // Timer state
    let timerInterval = null;
    let startTime = 0;
    let accumulatedTime = 0;
    let isWalking = false;

    // Custom blue marker SVG pin with beautiful pulse ring
    const bluePinIcon = L.divIcon({
        className: 'custom-blue-pin',
        html: `
            <div class="pin-wrapper">
                <div class="pin-pulse"></div>
                <svg class="pin-svg" viewBox="0 0 24 24" width="36" height="36">
                    <path fill="#3B82F6" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                </svg>
            </div>
        `,
        iconSize: [36, 36],
        iconAnchor: [18, 36]
    });

    function initMap() {
        // Tokyo Station as default center
        const defaultLat = 35.681236;
        const defaultLng = 139.767125;
        
        map = L.map('map', {
            zoomControl: true,
            scrollWheelZoom: true
        }).setView([defaultLat, defaultLng], 13);
        
        // Standard OpenStreetMap tiles as required
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Call invalidateSize after transition / rendering to align layout
        setTimeout(() => {
            map.invalidateSize();
            // Restore photos if any exist in localStorage
            restoreCapturedPhotos();
            // Check for walk recovery after map is loaded
            checkWalkRecovery();
            // Load and display last saved walk route if present
            loadLastWalk();
        }, 400);
    }

    initMap();

    // --- State Handler Functions ---
    
    /**
     * Show gentle floating toast notification
     */
    function showGentleToast(title, message, isError = true) {
        toastTitle.textContent = title;
        toastMessage.textContent = message;
        
        if (isError) {
            toastOverlay.classList.remove('theme-info');
            toastIcon.textContent = '⚠️';
        } else {
            toastOverlay.classList.add('theme-info');
            toastIcon.textContent = '💡';
        }
        
        toastOverlay.classList.add('active');
        
        // Auto-close after 8 seconds
        setTimeout(() => {
            closeToast();
        }, 8000);
    }
    
    function closeToast() {
        toastOverlay.classList.remove('active');
    }
    
    toastCloseBtn.addEventListener('click', closeToast);
    
    // --- Helper Logic for Route Tracking ---
    
    /**
     * Calculates distance between two coordinates in meters using Haversine formula
     */
    function calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371000; // Earth's radius in meters
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = 
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    /**
     * Formats milliseconds into HH:MM:SS
     */
    function formatTime(ms) {
        const totalSeconds = Math.floor(ms / 1000);
        const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
        const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
        const seconds = String(totalSeconds % 60).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    // --- Backup & LocalStorage Operations ---
    
    function saveWalkBackup() {
        localStorage.setItem('aruku_walk_path', JSON.stringify(walkPath));
        localStorage.setItem('aruku_walk_distance', totalDistance.toString());
        localStorage.setItem('aruku_walk_start_time', startTime.toString());
        localStorage.setItem('aruku_walk_accumulated', accumulatedTime.toString());
        localStorage.setItem('aruku_walk_status', 'walking');
    }

    function clearWalkBackup() {
        localStorage.removeItem('aruku_walk_path');
        localStorage.removeItem('aruku_walk_distance');
        localStorage.removeItem('aruku_walk_start_time');
        localStorage.removeItem('aruku_walk_accumulated');
        localStorage.removeItem('aruku_walk_status');
        
        // Clear camera photos data and reset map layers
        localStorage.removeItem('aruku_photos');
        photoMarkers.forEach(marker => {
            if (map) map.removeLayer(marker);
        });
        photoMarkers = [];
        capturedPhotos = [];
    }

    // --- Route Tracking Handlers ---

    function handlePositionUpdate(position) {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const accuracy = position.coords.accuracy;
        const timestamp = new Date(position.timestamp);
        
        // Update currentLocation for camera use
        currentLocation = [lat, lng];
        
        // Precision numbers up to 6 decimal places
        valLatitude.textContent = lat.toFixed(6);
        valLongitude.textContent = lng.toFixed(6);
        valAccuracy.textContent = Math.round(accuracy).toLocaleString();
        valAccuracyUnit.textContent = 'メートル';
        
        const hours = String(timestamp.getHours()).padStart(2, '0');
        const minutes = String(timestamp.getMinutes()).padStart(2, '0');
        const seconds = String(timestamp.getSeconds()).padStart(2, '0');
        valTimestamp.textContent = `${hours}:${minutes}:${seconds}`;
        
        locationCard.classList.add('show-card');
        radarContainer.classList.remove('is-locating');
        radarContainer.classList.add('has-coords');
        
        // Filter out highly inaccurate GPS noise points if we already have some points
        if (accuracy > 35 && walkPath.length > 0) {
            console.warn(`Poor GPS accuracy skipped: ${accuracy}m`);
            return; 
        }
        
        const currentCoord = [lat, lng];
        
        // Calculate Distance
        if (walkPath.length > 0) {
            const prev = walkPath[walkPath.length - 1];
            const dist = calculateDistance(prev[0], prev[1], lat, lng);
            
            // Only add distance if there's real movement (e.g. > 2 meters) to filter out jitter
            if (dist > 2) {
                totalDistance += dist;
                walkDistance.textContent = Math.round(totalDistance).toLocaleString();
            }
        }
        
        // Push coordinate to walkPath
        walkPath.push(currentCoord);
        saveWalkBackup();
        
        // Update Map Polyline
        if (polyline) {
            polyline.setLatLngs(walkPath);
        } else {
            polyline = L.polyline(walkPath, {
                color: '#FF3B30',
                weight: 6,
                opacity: 0.9,
                lineCap: 'round',
                lineJoin: 'round'
            }).addTo(map);
        }
        
        // Update pulsing marker location
        if (marker) {
            marker.setLatLng([lat, lng]);
        } else {
            marker = L.marker([lat, lng], { icon: bluePinIcon }).addTo(map);
        }
        
        // Pan to location gently
        map.panTo([lat, lng]);
        
        if (navigator.vibrate && walkPath.length === 1) {
            navigator.vibrate([80]);
        }
    }

    function handlePositionError(error) {
        let errorTitle = '位置情報の取得エラー';
        let errorMessage = '追跡中に一時的にGPS信号が途切れました。電波の良い場所に移動してください。';
        
        switch (error.code) {
            case error.PERMISSION_DENIED:
                errorTitle = '位置情報が許可されていません';
                errorMessage = '位置情報の利用許可を設定からオンにしてください。';
                break;
            case error.TIMEOUT:
                errorTitle = '接続タイムアウト';
                errorMessage = '位置情報の取得でタイムアウトが発生しました。';
                break;
        }
        
        showGentleToast(errorTitle, errorMessage);
        console.warn(`watchPosition Error: [${error.code}] ${error.message}`);
    }

    // --- Main Tracking Functions ---
    
    function startWalk(resume = false) {
        if (isWalking) return;
        isWalking = true;
        
        // Reset radar and details state in case
        radarContainer.classList.add('is-locating');
        radarContainer.classList.remove('has-coords');
        locationCard.classList.remove('show-card');
        
        // UI Adjustments
        startWalkBtn.classList.add('hidden');
        getBtn.classList.add('hidden');
        endWalkBtn.classList.remove('hidden');
        statsPanel.classList.add('active');
        
        // Reset or recover state
        if (!resume) {
            walkPath = [];
            totalDistance = 0;
            accumulatedTime = 0;
            startTime = Date.now();
            lastPosition = null;
            
            // Clear map layers if they exist
            if (polyline) {
                map.removeLayer(polyline);
                polyline = null;
            }
            if (marker) {
                map.removeLayer(marker);
                marker = null;
            }
            
            walkTime.textContent = '00:00:00';
            walkDistance.textContent = '0';
            
            saveWalkBackup();
        } else {
            // Restore from localStorage
            try {
                walkPath = JSON.parse(localStorage.getItem('aruku_walk_path')) || [];
                totalDistance = parseFloat(localStorage.getItem('aruku_walk_distance')) || 0;
                accumulatedTime = parseFloat(localStorage.getItem('aruku_walk_accumulated')) || 0;
                startTime = parseFloat(localStorage.getItem('aruku_walk_start_time')) || Date.now();
            } catch (e) {
                console.error("Failed to restore walk backup", e);
                walkPath = [];
                totalDistance = 0;
                accumulatedTime = 0;
                startTime = Date.now();
            }
            
            // Redraw path
            if (walkPath.length > 0) {
                polyline = L.polyline(walkPath, {
                    color: '#FF3B30',
                    weight: 6,
                    opacity: 0.9,
                    lineCap: 'round',
                    lineJoin: 'round'
                }).addTo(map);
                
                // Set marker to the last position
                const last = walkPath[walkPath.length - 1];
                currentLocation = last;
                if (marker) {
                    map.removeLayer(marker);
                }
                marker = L.marker(last, { icon: bluePinIcon }).addTo(map);
                map.setView(last, 17);
                
                // Show location card with recovered coordinates
                valLatitude.textContent = last[0].toFixed(6);
                valLongitude.textContent = last[1].toFixed(6);
                valAccuracy.textContent = '--';
                valAccuracyUnit.textContent = '';
                valTimestamp.textContent = '復元データ';
                locationCard.classList.add('show-card');
                radarContainer.classList.add('has-coords');
            }
            
            walkDistance.textContent = Math.round(totalDistance).toLocaleString();
        }
        
        gpsStatusBadge.textContent = 'Walking Log';
        gpsStatusBadge.className = 'status-badge status-locating';
        
        // Start Geolocation watchPosition
        if (navigator.geolocation) {
            watchId = navigator.geolocation.watchPosition(
                handlePositionUpdate,
                handlePositionError,
                {
                    enableHighAccuracy: true,
                    timeout: 12000,
                    maximumAge: 0
                }
            );
        } else {
            showGentleToast(
                'GPSエラー',
                'このブラウザはGPS追跡に対応していません。'
            );
            stopWalkUI();
            return;
        }
        
        // Start Timer Interval
        timerInterval = setInterval(() => {
            const elapsed = Date.now() - startTime + accumulatedTime;
            walkTime.textContent = formatTime(elapsed);
        }, 1000);
        
        showGentleToast('散歩を開始しました！', 'GPSでのルート追跡を開始しました。歩き始めましょう！', false);
        
        if (navigator.vibrate) {
            navigator.vibrate([100, 50, 100]);
        }
    }

    function endWalk() {
        if (!isWalking) return;
        
        // Clear watch Position
        if (watchId !== null) {
            navigator.geolocation.clearWatch(watchId);
            watchId = null;
        }
        
        // Stop timer
        if (timerInterval !== null) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        
        const finalElapsedMs = Date.now() - startTime + accumulatedTime;
        const finalTimeStr = formatTime(finalElapsedMs);
        const finalDistanceStr = `${Math.round(totalDistance).toLocaleString()} m`;
        
        // Show summary modal
        summaryTime.textContent = finalTimeStr;
        summaryDistance.textContent = finalDistanceStr;
        summaryOverlay.classList.add('active');
        
        // Adjust map bounds to fit the entire route
        if (walkPath.length > 0 && map) {
            const bounds = L.latLngBounds(walkPath);
            map.fitBounds(bounds, {
                padding: [50, 50],
                maxZoom: 17,
                animate: true,
                duration: 1.8
            });
        }
        
        // Reset walk state
        isWalking = false;
        clearWalkBackup();
        
        // Reset UI buttons
        stopWalkUI();
        
        if (navigator.vibrate) {
            navigator.vibrate([150, 100, 150]);
        }
    }

    function stopWalkUI() {
        isWalking = false;
        startWalkBtn.classList.remove('hidden');
        getBtn.classList.remove('hidden');
        endWalkBtn.classList.add('hidden');
        statsPanel.classList.remove('active');
        
        gpsStatusBadge.textContent = 'GPS Ready';
        gpsStatusBadge.className = 'status-badge pulse-active';
    }

    function checkWalkRecovery() {
        const walkStatus = localStorage.getItem('aruku_walk_status');
        if (walkStatus === 'walking') {
            startWalk(true);
        }
    }

    // --- Click Event Listeners ---

    startWalkBtn.addEventListener('click', () => {
        startWalk(false);
    });

    endWalkBtn.addEventListener('click', () => {
        endWalk();
    });

    // --- 既存の endWalkBtn の処理の中に以下を組み込む ---
    endWalkBtn.addEventListener('click', () => {
        // 【既存の処理】タイマーを止める、ダイアログを出すなど
        // ...省略...

        // 【新規追加】LocalStorageに保存する処理
        const newLog = {
            id: Date.now(), 
            date: new Date().toLocaleDateString('ja-JP'), 
            time: walkTime.textContent,       // 画面上の現在の時間テキストを取得
            distance: walkDistance.textContent // 画面上の現在の距離テキストを取得
        };

        let walkHistory = JSON.parse(localStorage.getItem('aruku_walk_history')) || [];
        walkHistory.unshift(newLog); // 最新を先頭に追加
        localStorage.setItem('aruku_walk_history', JSON.stringify(walkHistory));

        // 表示を更新
        displayHistory();
    });




    closeSummaryBtn.addEventListener('click', () => {
        summaryOverlay.classList.remove('active');
    });

    // --- Camera & Photo Event Listeners & Helpers ---

    // Trigger file input when camera button is clicked
    takePhotoBtn.addEventListener('click', () => {
        // Double check if we have GPS location first
        if (!currentLocation) {
            showGentleToast(
                '位置情報がありません',
                '写真を撮影する前に、現在地を取得するか、散歩を開始してください。'
            );
            return;
        }
        cameraInput.click();
    });

    // Handle captured photo
    cameraInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) return;

        // Verify location is available
        if (!currentLocation) {
            showGentleToast(
                '位置情報がありません',
                '写真を保存する位置情報が特定できませんでした。再度位置情報を取得してください。'
            );
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const img = new Image();
            img.onload = function() {
                // Compress image to fit within max 800px width/height for localStorage safety
                const canvas = document.createElement('canvas');
                let width = img.width;
                let height = img.height;
                const maxSize = 800;

                if (width > height) {
                    if (width > maxSize) {
                        height *= maxSize / width;
                        width = maxSize;
                    }
                } else {
                    if (height > maxSize) {
                        width *= maxSize / height;
                        height = maxSize;
                    }
                }

                canvas.width = width;
                canvas.height = height;

                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                // Compress as JPEG with 0.7 quality
                const compressedBase64 = canvas.toDataURL('image/jpeg', 0.7);

                // Get current timestamp formatted
                const now = new Date();
                const hours = String(now.getHours()).padStart(2, '0');
                const minutes = String(now.getMinutes()).padStart(2, '0');
                const seconds = String(now.getSeconds()).padStart(2, '0');
                const timestamp = `${hours}:${minutes}:${seconds}`;

                // Create and place photo marker on Leaflet map
                createPhotoMarker(compressedBase64, currentLocation, timestamp, true);

                // Clear input value so same photo file can be selected again if needed
                cameraInput.value = '';

                // Micro-vibration feedback
                if (navigator.vibrate) {
                    navigator.vibrate([100]);
                }

                showGentleToast('写真を撮影しました！', '地図上に撮影した写真を配置しました。タップで拡大表示できます。', false);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });

    /**
     * Create and place a circular photo thumbnail marker on the Leaflet map
     */
    function createPhotoMarker(image, coords, timestamp, save = true) {
        if (!map) return;

        // Custom Leaflet DivIcon containing the circular thumbnail
        const photoIcon = L.divIcon({
            className: 'photo-marker-icon',
            html: `<img src="${image}" class="photo-marker-img" />`,
            iconSize: [44, 44],
            iconAnchor: [22, 22]
        });

        // Add Leaflet marker at coords
        const photoMarker = L.marker(coords, { icon: photoIcon }).addTo(map);

        // Custom popup zoom trigger on marker click
        photoMarker.on('click', () => {
            showPhotoModal(image, coords, timestamp);
        });

        // Keep reference of marker for removal on reset
        photoMarkers.push(photoMarker);

        // Save to capturedPhotos array and localStorage if requested
        if (save) {
            const photoData = {
                image: image,
                coords: coords,
                timestamp: timestamp
            };
            capturedPhotos.push(photoData);
            try {
                localStorage.setItem('aruku_photos', JSON.stringify(capturedPhotos));
            } catch (error) {
                console.error("Failed to save photo to localStorage", error);
                showGentleToast('保存エラー', '端末の容量制限により写真を保存できませんでしたが、地図には表示されます。');
            }
        }
    }

    /**
     * Show premium glassmorphic modal with large photo preview
     */
    function showPhotoModal(image, coords, timestamp) {
        photoPreviewImg.src = image;
        photoCaption.innerHTML = `📍 撮影場所: 緯度 ${coords[0].toFixed(6)}, 経度 ${coords[1].toFixed(6)}<br>⏱️ 撮影時刻: ${timestamp}`;
        photoOverlay.classList.add('active');
        
        if (navigator.vibrate) {
            navigator.vibrate([50]);
        }
    }

    /**
     * Close the photo preview modal
     */
    function closePhotoModal() {
        photoOverlay.classList.remove('active');
    }

    // Modal close event listeners
    photoCloseBtn.addEventListener('click', closePhotoModal);
    
    // Close modal when tapping overlay background outside the card
    photoOverlay.addEventListener('click', (event) => {
        if (event.target === photoOverlay) {
            closePhotoModal();
        }
    });

    /**
     * Restore captured photos from localStorage and place on Leaflet map
     */
    function restoreCapturedPhotos() {
        try {
            const stored = localStorage.getItem('aruku_photos');
            if (stored) {
                capturedPhotos = JSON.parse(stored) || [];
                capturedPhotos.forEach(photo => {
                    createPhotoMarker(photo.image, photo.coords, photo.timestamp, false);
                });
            }
        } catch (e) {
            console.error("Failed to restore photos", e);
        }
    }

    // Load and render last saved walk route on startup
    function loadLastWalk() {
        const savedPath = localStorage.getItem('aruku_last_walk_path');
        const savedDistance = localStorage.getItem('aruku_last_walk_distance');
        const savedTime = localStorage.getItem('aruku_last_walk_time');
        if (savedPath && savedDistance && savedTime) {
            try {
                const path = JSON.parse(savedPath);
                if (path.length > 0 && map) {
                    // Draw polyline
                    const poly = L.polyline(path, {
                        color: '#FF3B30',
                        weight: 6,
                        opacity: 0.9,
                        lineCap: 'round',
                        lineJoin: 'round'
                    }).addTo(map);
                    // Place marker at last point
                    const last = path[path.length - 1];
                    L.marker(last, { icon: bluePinIcon }).addTo(map);
                    // Fit map to route
                    const bounds = L.latLngBounds(path);
                    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 17, animate: true, duration: 1.8 });
                    // Show summary overlay
                    summaryTime.textContent = savedTime;
                    summaryDistance.textContent = `${Math.round(parseFloat(savedDistance)).toLocaleString()} m`;
                    summaryOverlay.classList.add('active');
                }
            } catch (e) {
                console.error('Failed to load last walk', e);
            }
        }
    }

    // === 履歴表示用関数（LocalStorageから読み込んでHTMLを生成） ===
    function displayHistory() {
        const historyContainer = document.getElementById('history-list');
        if (!historyContainer) return;

        // LocalStorageからデータを取得（なければ空の配列）
        const walkHistory = JSON.parse(localStorage.getItem('aruku_walk_history')) || [];

        // 一旦表示をクリア
        historyContainer.innerHTML = '';

        if (walkHistory.length === 0) {
            historyContainer.innerHTML = '<p class="text-muted" style="text-align:center; padding:20px;">まだ散歩の履歴はありません。</p>';
            return;
        }

        // 履歴をループしてHTMLを生成
        walkHistory.forEach(log => {
            const item = document.createElement('div');
            // 将来的にファイルダウンロードボタンを追加しやすいようにクラスを付与
            item.className = 'history-item'; 
            item.innerHTML = `
                <div class="history-date">${log.date}</div>
                <div class="history-details">
                    <span>⏱️ ${log.time}</span>
                    <span>🛣️ ${log.distance}</span>
                </div>
            `;
            historyContainer.appendChild(item);
        });
    }

    // --- Original Single Geolocation Fetch Button ---
    
    getBtn.addEventListener('click', () => {
        if (!navigator.geolocation) {
            gpsStatusBadge.textContent = 'GPS Error';
            gpsStatusBadge.className = 'status-badge status-error';
            showGentleToast(
                'お使いの端末は非対応です',
                'ブラウザが位置情報の取得に対応していないため、現在地を取得できませんでした。'
            );
            return;
        }

        // Button loading state
        getBtn.classList.add('is-loading');
        getBtn.disabled = true;
        btnText.textContent = '現在地を探索中...';
        btnIcon.textContent = '🌀';
        
        // Radar visual sweep active
        radarContainer.classList.add('is-locating');
        radarContainer.classList.remove('has-coords');
        
        // Status badge updates
        gpsStatusBadge.textContent = 'Searching...';
        gpsStatusBadge.className = 'status-badge status-locating';
        
        // Hide previous results smoothly
        locationCard.classList.remove('show-card');
        closeToast();

        const geoOptions = {
            enableHighAccuracy: true,
            timeout: 12000,
            maximumAge: 0
        };

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                const accuracy = position.coords.accuracy;
                const timestamp = new Date(position.timestamp);

                // Update currentLocation for camera use
                currentLocation = [lat, lng];

                valLatitude.textContent = lat.toFixed(6);
                valLongitude.textContent = lng.toFixed(6);
                valAccuracy.textContent = Math.round(accuracy).toLocaleString();
                valAccuracyUnit.textContent = 'メートル';
                
                const hours = String(timestamp.getHours()).padStart(2, '0');
                const minutes = String(timestamp.getMinutes()).padStart(2, '0');
                const seconds = String(timestamp.getSeconds()).padStart(2, '0');
                valTimestamp.textContent = `${hours}:${minutes}:${seconds}`;

                // Reset button
                getBtn.classList.remove('is-loading');
                getBtn.disabled = false;
                btnText.textContent = '現在地';
                btnIcon.textContent = '🎯';
                
                radarContainer.classList.remove('is-locating');
                radarContainer.classList.add('has-coords');
                
                gpsStatusBadge.textContent = 'Active GPS';
                gpsStatusBadge.className = 'status-badge';
                
                locationCard.classList.add('show-card');

                if (map) {
                    map.invalidateSize();
                    
                    if (marker) {
                        map.removeLayer(marker);
                    }
                    if (polyline) {
                        map.removeLayer(polyline);
                        polyline = null;
                    }
                    
                    marker = L.marker([lat, lng], { icon: bluePinIcon }).addTo(map);
                    
                    map.flyTo([lat, lng], 17, {
                        animate: true,
                        duration: 2.2
                    });
                }
                
                if (navigator.vibrate) {
                    navigator.vibrate([80, 50, 80]);
                }
            },
            (error) => {
                getBtn.classList.remove('is-loading');
                getBtn.disabled = false;
                btnText.textContent = '現在地';
                btnIcon.textContent = '🎯';
                
                radarContainer.classList.remove('is-locating');
                radarContainer.classList.remove('has-coords');
                
                gpsStatusBadge.textContent = 'GPS Error';
                gpsStatusBadge.className = 'status-badge status-error';
                
                locationCard.classList.remove('show-card');
                
                let errorTitle = '位置情報の取得エラー';
                let errorMessage = '取得できませんでした。電波の良い場所に移動して再度お試しください。';
                
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorTitle = '位置情報が許可されていません';
                        errorMessage = '位置情報の利用設定がオフになっています。端末の設定から位置情報の使用許可（オン）にしてから再度お試しください。';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorTitle = '現在地を特定できませんでした';
                        errorMessage = 'GPSの信号が十分に受信できないか、基地局からの情報が取得できません。';
                        break;
                    case error.TIMEOUT:
                        errorTitle = '接続タイムアウト';
                        errorMessage = '位置情報の通信タイムアウトが発生しました。';
                        break;
                }

                showGentleToast(errorTitle, errorMessage);
                console.warn(`Geolocation Error [Code ${error.code}]: ${error.message}`);
            },
            geoOptions
        );
    });

    // 【新規追加】起動時に過去の履歴を表示する
    displayHistory();
});
