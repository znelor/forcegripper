import 'dart:async';
import 'dart:collection';
import 'dart:io';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:permission_handler/permission_handler.dart';

void main() {
  runApp(const BLEPlotterApp());
}

class BLEPlotterApp extends StatelessWidget {
  const BLEPlotterApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HX711 BLE Plotter',
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: const Color(0xFF0d1117),
      ),
      home: const CalibrationPage(),
      debugShowCheckedModeBanner: false,
    );
  }
}

/// BLE Configuration
class BleConfig {
  static const String targetDeviceName = "HX711_Scale";
  static const String uartTxCharUuid = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";
  static const String hm10CharUuid = "0000ffe1-0000-1000-8000-00805f9b34fb";
}

/// Data point with timestamp
class DataPoint {
  final double time;
  final double value;
  DataPoint(this.time, this.value);
}

/// Singleton BLE Service
class BleDataService {
  static final BleDataService _instance = BleDataService._internal();
  factory BleDataService() => _instance;
  BleDataService._internal();

  BluetoothDevice? _connectedDevice;
  StreamSubscription<List<int>>? _dataSubscription;
  StreamSubscription<BluetoothConnectionState>? _connectionSubscription;

  final _rawDataController = StreamController<double>.broadcast();
  Stream<double> get rawDataStream => _rawDataController.stream;

  final _connectionController = StreamController<String>.broadcast();
  Stream<String> get connectionStream => _connectionController.stream;

  bool _isConnected = false;
  bool get isConnected => _isConnected;

  String _statusMessage = "Initializing...";
  String get statusMessage => _statusMessage;

  String? _deviceName;
  String? get deviceName => _deviceName;

  String _dataBuffer = "";

  // Calibration
  double _minForce = 0;
  double _maxForce = 4095;

  double get minForce => _minForce;
  double get maxForce => _maxForce;

  void setCalibration(double min, double max) {
    if (max > min) {
      _minForce = min;
      _maxForce = max;
    }
  }

  double get normalizedForce {
    if (_lastValue == null) return 0.0;
    if (_lastValue! <= _minForce) return 0.0;
    if (_lastValue! >= _maxForce) return 1.0;
    return (_lastValue! - _minForce) / (_maxForce - _minForce);
  }

  double? _lastValue;
  double? get lastValue => _lastValue;

  // Rate tracking
  int _packetCount = 0;
  int _packetsPerSecond = 0;
  Timer? _ppsTimer;
  int get packetsPerSecond => _packetsPerSecond;

  bool _isConnecting = false;
  bool _shouldRetry = true;

  void _updateStatus(String message) {
    _statusMessage = message;
    _connectionController.add(message);
    debugPrint('BLE: $message');
  }

  Future<bool> _requestPermissions() async {
    if (Platform.isAndroid) {
      Map<Permission, PermissionStatus> statuses = await [
        Permission.bluetoothScan,
        Permission.bluetoothConnect,
        Permission.location,
      ].request();
      return statuses.values.every(
        (status) => status.isGranted || status.isLimited,
      );
    }
    return true;
  }

  void startAutoConnect() {
    if (_isConnecting || _isConnected) return;
    _shouldRetry = true;
    _attemptConnection();
  }

  void stopAutoConnect() {
    _shouldRetry = false;
  }

  Future<void> _attemptConnection() async {
    if (_isConnecting || _isConnected || !_shouldRetry) return;
    _isConnecting = true;

    _updateStatus("Checking permissions...");

    bool hasPermissions = await _requestPermissions();
    if (!hasPermissions) {
      _updateStatus("Permissions denied");
      _isConnecting = false;
      _scheduleRetry();
      return;
    }

    BluetoothAdapterState state = await FlutterBluePlus.adapterState.first;
    if (state != BluetoothAdapterState.on) {
      _updateStatus("Bluetooth is OFF");
      _isConnecting = false;
      _scheduleRetry();
      return;
    }

    _updateStatus("Scanning...");

    try {
      await FlutterBluePlus.startScan(
        timeout: const Duration(seconds: 10),
        androidUsesFineLocation: true,
      );

      bool found = false;
      await for (List<ScanResult> results in FlutterBluePlus.scanResults) {
        for (ScanResult result in results) {
          String name = result.device.platformName;
          if (name.isEmpty) name = result.advertisementData.advName;

          if (name == BleConfig.targetDeviceName) {
            await FlutterBluePlus.stopScan();
            found = true;
            await _connectToDevice(result.device);
            break;
          }
        }
        if (found || !_shouldRetry) break;
      }

      if (!found && !_isConnected) {
        _updateStatus("Device not found");
        _scheduleRetry();
      }
    } catch (e) {
      _updateStatus("Scan error: $e");
      _scheduleRetry();
    }

    _isConnecting = false;
  }

  void _scheduleRetry() {
    if (!_shouldRetry || _isConnected) return;
    Future.delayed(const Duration(seconds: 3), () {
      if (_shouldRetry && !_isConnected && !_isConnecting) {
        _attemptConnection();
      }
    });
  }

  Future<void> _connectToDevice(BluetoothDevice device) async {
    try {
      _updateStatus("Connecting...");

      _connectionSubscription?.cancel();
      _connectionSubscription = device.connectionState.listen((state) {
        if (state == BluetoothConnectionState.disconnected) {
          _handleDisconnect();
        }
      });

      await device.connect(timeout: const Duration(seconds: 10));
      _connectedDevice = device;
      _deviceName = device.platformName;

      _updateStatus("Discovering services...");

      List<BluetoothService> services = await device.discoverServices();

      BluetoothCharacteristic? dataChar;
      for (BluetoothService service in services) {
        for (BluetoothCharacteristic char in service.characteristics) {
          String uuid = char.uuid.toString().toLowerCase();
          if (uuid == BleConfig.uartTxCharUuid.toLowerCase() ||
              uuid == BleConfig.hm10CharUuid.toLowerCase()) {
            if (char.properties.notify) {
              dataChar = char;
              break;
            }
          }
        }
        if (dataChar != null) break;
      }

      if (dataChar == null) {
        _updateStatus("No data characteristic");
        await device.disconnect();
        _scheduleRetry();
        return;
      }

      await dataChar.setNotifyValue(true);

      _dataSubscription?.cancel();
      _dataSubscription = dataChar.onValueReceived.listen(_handleData);

      _ppsTimer?.cancel();
      _ppsTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
        _packetsPerSecond = _packetCount;
        _packetCount = 0;
      });

      _isConnected = true;
      _updateStatus("Connected");
    } catch (e) {
      _updateStatus("Connection failed");
      _handleDisconnect();
    }
  }

  void _handleData(List<int> data) {
    try {
      String text = String.fromCharCodes(data);
      _dataBuffer += text;

      while (_dataBuffer.contains('\n')) {
        int idx = _dataBuffer.indexOf('\n');
        String line = _dataBuffer.substring(0, idx).trim();
        _dataBuffer = _dataBuffer.substring(idx + 1);

        if (line.isNotEmpty) {
          double? value = double.tryParse(line);
          if (value != null) {
            _packetCount++;
            _lastValue = value;
            _rawDataController.add(value);
          }
        }
      }
    } catch (e) {
      // Ignore
    }
  }

  void _handleDisconnect() {
    _isConnected = false;
    _connectedDevice = null;
    _dataSubscription?.cancel();
    _ppsTimer?.cancel();
    _updateStatus("Disconnected");
    _scheduleRetry();
  }

  Future<void> disconnect() async {
    _shouldRetry = false;
    await _dataSubscription?.cancel();
    await _connectionSubscription?.cancel();
    await _connectedDevice?.disconnect();
    _ppsTimer?.cancel();
    _isConnected = false;
    _connectedDevice = null;
  }
}

// ============================================================================
// CALIBRATION PAGE
// ============================================================================

class CalibrationPage extends StatefulWidget {
  const CalibrationPage({super.key});

  @override
  State<CalibrationPage> createState() => _CalibrationPageState();
}

class _CalibrationPageState extends State<CalibrationPage> {
  final BleDataService _ble = BleDataService();

  double _currentValue = 0;
  double _baselineValue = 0;
  double _peakValue = 0;
  bool _baselineSet = false;

  bool _isConnected = false;

  // Game settings
  double _holdDuration = 3.0; // 1-6 seconds
  double _zoneWidth = 0.15; // 0.10-0.30 (10-30%)

  @override
  void initState() {
    super.initState();
    _initBle();
  }

  void _initBle() {
    _ble.connectionStream.listen((status) {
      if (mounted) {
        setState(() {
          _isConnected = _ble.isConnected;
        });
      }
    });

    _ble.rawDataStream.listen((value) {
      if (mounted) {
        setState(() {
          _currentValue = value;
          if (_baselineSet && value > _peakValue) {
            _peakValue = value;
          }
        });
      }
    });

    _ble.startAutoConnect();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0d1117),
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildCurrentValue(),
                    const SizedBox(height: 24),
                    _buildBaselineCard(),
                    const SizedBox(height: 16),
                    _buildPeakCard(),
                    const SizedBox(height: 24),
                    _buildGameSettings(),
                    const SizedBox(height: 24),
                    _buildButtons(),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    Color statusColor = _isConnected
        ? const Color(0xFF3fb950)
        : const Color(0xFFd29922);
    IconData statusIcon = _isConnected
        ? Icons.bluetooth_connected
        : Icons.bluetooth_searching;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        color: Color(0xFF161b22),
        border: Border(bottom: BorderSide(color: Color(0xFF30363d))),
      ),
      child: Row(
        children: [
          const Expanded(
            child: Text(
              'Force Sensor Setup',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFFf0f6fc),
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: const Color(0xFF21262d),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: statusColor),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(statusIcon, color: statusColor, size: 14),
                const SizedBox(width: 4),
                Text(
                  _isConnected ? 'OK' : '...',
                  style: TextStyle(color: statusColor, fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCurrentValue() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF161b22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF30363d)),
      ),
      child: Column(
        children: [
          const Text(
            'Current Reading',
            style: TextStyle(color: Color(0xFF8b949e), fontSize: 14),
          ),
          const SizedBox(height: 8),
          Text(
            _currentValue.toStringAsFixed(0),
            style: const TextStyle(
              color: Color(0xFF58a6ff),
              fontSize: 48,
              fontWeight: FontWeight.bold,
              fontFamily: 'monospace',
            ),
          ),
          if (_isConnected)
            Text(
              '${_ble.packetsPerSecond} Hz',
              style: const TextStyle(color: Color(0xFF8b949e), fontSize: 12),
            ),
        ],
      ),
    );
  }

  Widget _buildBaselineCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _baselineSet ? const Color(0xFF1a2f1a) : const Color(0xFF161b22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _baselineSet
              ? const Color(0xFF3fb950)
              : const Color(0xFF30363d),
        ),
      ),
      child: Column(
        children: [
          const Text(
            'Step 1: Relax Grip (Baseline)',
            style: TextStyle(color: Color(0xFFf0f6fc), fontSize: 16),
          ),
          const SizedBox(height: 12),
          ElevatedButton(
            onPressed: _isConnected
                ? () {
                    setState(() {
                      _baselineValue = _currentValue;
                      _baselineSet = true;
                      if (_peakValue <= _baselineValue) {
                        _peakValue = _baselineValue + 1000;
                      }
                    });
                  }
                : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF238636),
              foregroundColor: Colors.white,
              disabledBackgroundColor: const Color(0xFF21262d),
            ),
            child: const Text('Set Baseline (0%)'),
          ),
          if (_baselineSet)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Baseline: ${_baselineValue.toStringAsFixed(0)}',
                style: const TextStyle(color: Color(0xFF3fb950)),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildPeakCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF161b22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF30363d)),
      ),
      child: Column(
        children: [
          const Text(
            'Step 2: Squeeze Hard (Max Force)',
            style: TextStyle(color: Color(0xFFf0f6fc), fontSize: 16),
          ),
          const SizedBox(height: 8),
          Text(
            'Peak: ${_peakValue.toStringAsFixed(0)}',
            style: const TextStyle(
              color: Color(0xFFf85149),
              fontSize: 28,
              fontWeight: FontWeight.bold,
              fontFamily: 'monospace',
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Squeeze sensor - peak updates automatically',
            style: TextStyle(color: Color(0xFF8b949e), fontSize: 12),
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () {
              setState(() {
                _peakValue = _baselineValue;
              });
            },
            child: const Text('Reset Peak'),
          ),
        ],
      ),
    );
  }

  Widget _buildGameSettings() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF161b22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF30363d)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Game Settings',
            style: TextStyle(
              color: Color(0xFFf0f6fc),
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          // Hold Duration
          Row(
            children: [
              const SizedBox(
                width: 100,
                child: Text(
                  'Hold Time',
                  style: TextStyle(color: Color(0xFF8b949e), fontSize: 14),
                ),
              ),
              Expanded(
                child: SliderTheme(
                  data: SliderTheme.of(context).copyWith(
                    activeTrackColor: const Color(0xFF8957e5),
                    inactiveTrackColor: const Color(0xFF30363d),
                    thumbColor: const Color(0xFF8957e5),
                    overlayColor: const Color(0xFF8957e5).withOpacity(0.2),
                  ),
                  child: Slider(
                    value: _holdDuration,
                    min: 1.0,
                    max: 6.0,
                    divisions: 10,
                    onChanged: (value) {
                      setState(() {
                        _holdDuration = value;
                      });
                    },
                  ),
                ),
              ),
              SizedBox(
                width: 50,
                child: Text(
                  '${_holdDuration.toStringAsFixed(1)}s',
                  style: const TextStyle(
                    color: Color(0xFF8957e5),
                    fontWeight: FontWeight.bold,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          // Zone Width
          Row(
            children: [
              const SizedBox(
                width: 100,
                child: Text(
                  'Zone Size',
                  style: TextStyle(color: Color(0xFF8b949e), fontSize: 14),
                ),
              ),
              Expanded(
                child: SliderTheme(
                  data: SliderTheme.of(context).copyWith(
                    activeTrackColor: const Color(0xFF3fb950),
                    inactiveTrackColor: const Color(0xFF30363d),
                    thumbColor: const Color(0xFF3fb950),
                    overlayColor: const Color(0xFF3fb950).withOpacity(0.2),
                  ),
                  child: Slider(
                    value: _zoneWidth,
                    min: 0.05,
                    max: 0.40,
                    divisions: 7,
                    onChanged: (value) {
                      setState(() {
                        _zoneWidth = value;
                      });
                    },
                  ),
                ),
              ),
              SizedBox(
                width: 50,
                child: Text(
                  '${(_zoneWidth * 100).toStringAsFixed(0)}%',
                  style: const TextStyle(
                    color: Color(0xFF3fb950),
                    fontWeight: FontWeight.bold,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildButtons() {
    bool canStart = _isConnected && _baselineSet && _peakValue > _baselineValue;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Game Button
        ElevatedButton(
          onPressed: canStart
              ? () {
                  _ble.setCalibration(_baselineValue, _peakValue);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => ZoneHoldGame(
                        holdDuration: _holdDuration,
                        zoneWidth: _zoneWidth,
                      ),
                    ),
                  );
                }
              : null,
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF8957e5),
            foregroundColor: Colors.white,
            disabledBackgroundColor: const Color(0xFF21262d),
            padding: const EdgeInsets.symmetric(vertical: 18),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          child: const Text(
            '🎮  PLAY ZONE GAME',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ),
        const SizedBox(height: 12),
        // Plotter Button
        ElevatedButton(
          onPressed: canStart
              ? () {
                  _ble.setCalibration(_baselineValue, _peakValue);
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => const PlotterPage(),
                    ),
                  );
                }
              : null,
          style: ElevatedButton.styleFrom(
            backgroundColor: const Color(0xFF1f6feb),
            foregroundColor: Colors.white,
            disabledBackgroundColor: const Color(0xFF21262d),
            padding: const EdgeInsets.symmetric(vertical: 18),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
          ),
          child: const Text(
            '📊  VIEW PLOTTER',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ),
      ],
    );
  }
}

// ============================================================================
// ZONE HOLD GAME
// ============================================================================

class ZoneHoldGame extends StatefulWidget {
  final double holdDuration;
  final double zoneWidth;

  const ZoneHoldGame({
    super.key,
    this.holdDuration = 3.0,
    this.zoneWidth = 0.15,
  });

  @override
  State<ZoneHoldGame> createState() => _ZoneHoldGameState();
}

class _ZoneHoldGameState extends State<ZoneHoldGame>
    with TickerProviderStateMixin {
  final BleDataService _ble = BleDataService();
  final Random _random = Random();

  // Game config
  static const double gameMaxForce = 0.30; // Use only 30% of calibrated max

  // Game state
  double _currentForce = 0;
  double _targetCenter = 0.5; // center of target zone (0-1)
  double _holdProgress = 0; // 0 to 1
  bool _inZone = false;
  int _score = 0;
  int _round = 0;
  bool _completed = false;

  // Animations
  late AnimationController _pulseController;
  late AnimationController _popController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _popAnimation;

  // Particles for celebration
  List<Particle> _particles = [];

  Timer? _gameTimer;
  DateTime? _zoneEntryTime;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.15).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _popController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );

    _popAnimation = Tween<double>(begin: 1.0, end: 2.0).animate(
      CurvedAnimation(parent: _popController, curve: Curves.elasticOut),
    );

    _startNewRound();
    _initListeners();
    _startGameLoop();
  }

  void _initListeners() {
    _ble.rawDataStream.listen((value) {
      if (mounted) {
        setState(() {
          // Scale force: 30% of calibrated max = 100% in game
          _currentForce = (_ble.normalizedForce / gameMaxForce).clamp(0.0, 1.0);
        });
      }
    });
  }

  void _startGameLoop() {
    _gameTimer = Timer.periodic(const Duration(milliseconds: 16), (timer) {
      if (!mounted) return;

      double minZone = _targetCenter - widget.zoneWidth / 2;
      double maxZone = _targetCenter + widget.zoneWidth / 2;
      bool wasInZone = _inZone;
      _inZone = _currentForce >= minZone && _currentForce <= maxZone;

      if (_inZone && !_completed) {
        // Set entry time if we just entered OR if it was reset (new round)
        if (_zoneEntryTime == null) {
          _zoneEntryTime = DateTime.now();
          if (!wasInZone) {
            HapticFeedback.lightImpact();
          }
        }

        double elapsed =
            DateTime.now().difference(_zoneEntryTime!).inMilliseconds / 1000.0;
        _holdProgress = (elapsed / widget.holdDuration).clamp(0.0, 1.0);

        if (_holdProgress >= 1.0) {
          _onZoneComplete();
        }
      } else {
        if (wasInZone && !_completed) {
          // Left zone - reset progress with decay
          _holdProgress = (_holdProgress - 0.05).clamp(0.0, 1.0);
        } else {
          _holdProgress = (_holdProgress - 0.02).clamp(0.0, 1.0);
        }
        _zoneEntryTime = null;
      }

      // Update particles
      for (var p in _particles) {
        p.update();
      }
      _particles.removeWhere((p) => p.life <= 0);

      setState(() {});
    });
  }

  void _onZoneComplete() {
    _completed = true;
    _score += 100 + (_round * 10);
    HapticFeedback.heavyImpact();

    // Trigger pop animation
    _popController.forward(from: 0);

    // Spawn particles
    _spawnParticles();

    // Next round after delay
    Future.delayed(const Duration(milliseconds: 1500), () {
      if (mounted) {
        _startNewRound();
      }
    });
  }

  void _spawnParticles() {
    for (int i = 0; i < 30; i++) {
      _particles.add(
        Particle(
          x: 0.5,
          y: 0.5,
          vx: (_random.nextDouble() - 0.5) * 0.03,
          vy: (_random.nextDouble() - 0.5) * 0.03,
          color: HSLColor.fromAHSL(
            1.0,
            _random.nextDouble() * 60 + 100, // Green to yellow hue
            0.8,
            0.6,
          ).toColor(),
          size: _random.nextDouble() * 8 + 4,
        ),
      );
    }
  }

  void _startNewRound() {
    _round++;
    _completed = false;
    _holdProgress = 0;
    _zoneEntryTime = null;

    // Random target between 30% and 80%
    _targetCenter = 0.3 + _random.nextDouble() * 0.5;
  }

  @override
  void dispose() {
    _gameTimer?.cancel();
    _pulseController.dispose();
    _popController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0d1117),
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: _buildGameArea(),
              ),
            ),
            _buildStats(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: const BoxDecoration(
        color: Color(0xFF161b22),
        border: Border(bottom: BorderSide(color: Color(0xFF30363d))),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back, color: Color(0xFF8b949e)),
            onPressed: () => Navigator.pop(context),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'Zone Hold Game',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFFf0f6fc),
              ),
            ),
          ),
          Text(
            'Round $_round',
            style: const TextStyle(color: Color(0xFF8b949e), fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildGameArea() {
    double minZone = _targetCenter - widget.zoneWidth / 2;
    double maxZone = _targetCenter + widget.zoneWidth / 2;

    return LayoutBuilder(
      builder: (context, constraints) {
        return Container(
          decoration: BoxDecoration(
            color: const Color(0xFF161b22),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFF30363d)),
          ),
          child: Stack(
            children: [
              // Target zone background
              Positioned.fill(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(15),
                  child: CustomPaint(
                    painter: ZonePainter(
                      minZone: minZone,
                      maxZone: maxZone,
                      progress: _holdProgress,
                      inZone: _inZone,
                      completed: _completed,
                    ),
                  ),
                ),
              ),

              // Particles
              ..._particles.map((p) {
                return Positioned(
                  left: p.x * constraints.maxWidth - p.size / 2,
                  top: (1 - p.y) * constraints.maxHeight - p.size / 2,
                  child: Opacity(
                    opacity: p.life.clamp(0.0, 1.0),
                    child: Container(
                      width: p.size,
                      height: p.size,
                      decoration: BoxDecoration(
                        color: p.color,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                );
              }),

              // Current force indicator - same height as zone
              AnimatedBuilder(
                animation: _completed ? _popAnimation : _pulseAnimation,
                builder: (context, child) {
                  double scale = _completed
                      ? _popAnimation.value
                      : (_inZone ? _pulseAnimation.value : 1.0);

                  double opacity = _completed
                      ? (2.0 - _popAnimation.value).clamp(0.0, 1.0)
                      : 1.0;

                  // Player bar height matches zone height
                  double barHeight = widget.zoneWidth * constraints.maxHeight;
                  double barHalfHeight = barHeight / 2;

                  return Positioned(
                    left: 0,
                    right: 0,
                    bottom:
                        _currentForce * constraints.maxHeight - barHalfHeight,
                    child: Opacity(
                      opacity: opacity,
                      child: Transform.scale(
                        scale: scale,
                        child: Container(
                          height: barHeight,
                          margin: const EdgeInsets.symmetric(horizontal: 20),
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: _inZone
                                  ? [
                                      const Color(0xFF3fb950).withOpacity(0.9),
                                      const Color(0xFF2ea043).withOpacity(0.9),
                                    ]
                                  : [
                                      const Color(0xFFf85149).withOpacity(0.7),
                                      const Color(0xFFda3633).withOpacity(0.7),
                                    ],
                            ),
                            borderRadius: BorderRadius.circular(barHeight / 2),
                            boxShadow: [
                              BoxShadow(
                                color:
                                    (_inZone
                                            ? const Color(0xFF3fb950)
                                            : const Color(0xFFf85149))
                                        .withOpacity(0.4),
                                blurRadius: 20,
                                spreadRadius: 5,
                              ),
                            ],
                          ),
                          child: Center(
                            child: Text(
                              '${(_currentForce * 100).toStringAsFixed(0)}%',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: barHeight > 40 ? 24 : 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                },
              ),

              // Progress ring in center
              Center(
                child: SizedBox(
                  width: 180,
                  height: 180,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      // Background ring
                      CircularProgressIndicator(
                        value: 1.0,
                        strokeWidth: 12,
                        backgroundColor: const Color(0xFF30363d),
                        valueColor: const AlwaysStoppedAnimation(
                          Color(0xFF30363d),
                        ),
                      ),
                      // Progress ring
                      TweenAnimationBuilder<double>(
                        tween: Tween(begin: 0, end: _holdProgress),
                        duration: const Duration(milliseconds: 100),
                        builder: (context, value, child) {
                          return CircularProgressIndicator(
                            value: value,
                            strokeWidth: 12,
                            backgroundColor: Colors.transparent,
                            valueColor: AlwaysStoppedAnimation(
                              _completed
                                  ? const Color(0xFF3fb950)
                                  : Color.lerp(
                                      const Color(0xFFd29922),
                                      const Color(0xFF3fb950),
                                      value,
                                    )!,
                            ),
                          );
                        },
                      ),
                      // Center text
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (_completed)
                            const Text(
                              '✓',
                              style: TextStyle(
                                color: Color(0xFF3fb950),
                                fontSize: 48,
                              ),
                            )
                          else ...[
                            Text(
                              '${(_holdProgress * widget.holdDuration).toStringAsFixed(1)}s',
                              style: const TextStyle(
                                color: Color(0xFFf0f6fc),
                                fontSize: 32,
                                fontWeight: FontWeight.bold,
                                fontFamily: 'monospace',
                              ),
                            ),
                            Text(
                              'of ${widget.holdDuration.toStringAsFixed(0)}s',
                              style: const TextStyle(
                                color: Color(0xFF8b949e),
                                fontSize: 14,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ),

              // Target zone label
              Positioned(
                right: 10,
                top: (1 - _targetCenter) * constraints.maxHeight - 20,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFF21262d),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${(minZone * 100).toStringAsFixed(0)}-${(maxZone * 100).toStringAsFixed(0)}%',
                    style: const TextStyle(
                      color: Color(0xFF8b949e),
                      fontSize: 12,
                      fontFamily: 'monospace',
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStats() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: const BoxDecoration(
        color: Color(0xFF161b22),
        border: Border(top: BorderSide(color: Color(0xFF30363d))),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _statItem('Score', '$_score', const Color(0xFF3fb950)),
          _statItem(
            'Target',
            '${(_targetCenter * 100).toStringAsFixed(0)}%',
            const Color(0xFFd29922),
          ),
          _statItem(
            'Current',
            '${(_currentForce * 100).toStringAsFixed(0)}%',
            _inZone ? const Color(0xFF3fb950) : const Color(0xFF8b949e),
          ),
        ],
      ),
    );
  }

  Widget _statItem(String label, String value, Color valueColor) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: const TextStyle(color: Color(0xFF8b949e), fontSize: 12),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: TextStyle(
            color: valueColor,
            fontSize: 20,
            fontWeight: FontWeight.bold,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}

/// Painter for the target zone
class ZonePainter extends CustomPainter {
  final double minZone;
  final double maxZone;
  final double progress;
  final bool inZone;
  final bool completed;

  ZonePainter({
    required this.minZone,
    required this.maxZone,
    required this.progress,
    required this.inZone,
    required this.completed,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Zone boundaries (inverted Y)
    double top = (1 - maxZone) * size.height;
    double bottom = (1 - minZone) * size.height;
    double height = bottom - top;

    // Background zone (unfilled)
    final zoneBgPaint = Paint()
      ..color = const Color(0xFF21262d)
      ..style = PaintingStyle.fill;

    canvas.drawRect(Rect.fromLTWH(0, top, size.width, height), zoneBgPaint);

    // Filled portion based on progress
    Color fillColor;
    if (completed) {
      fillColor = const Color(0xFF3fb950).withOpacity(0.6);
    } else if (inZone) {
      fillColor = Color.lerp(
        const Color(0xFFd29922).withOpacity(0.3),
        const Color(0xFF3fb950).withOpacity(0.5),
        progress,
      )!;
    } else {
      fillColor = const Color(0xFF30363d).withOpacity(0.3);
    }

    final fillPaint = Paint()
      ..color = fillColor
      ..style = PaintingStyle.fill;

    // Fill from center outward
    double fillHeight = height * progress;
    double center = top + height / 2;

    canvas.drawRect(
      Rect.fromLTWH(0, center - fillHeight / 2, size.width, fillHeight),
      fillPaint,
    );

    // Zone border
    final borderPaint = Paint()
      ..color = inZone || completed
          ? const Color(0xFF3fb950).withOpacity(0.8)
          : const Color(0xFF484f58)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    canvas.drawRect(Rect.fromLTWH(0, top, size.width, height), borderPaint);

    // Dashed center line
    final centerPaint = Paint()
      ..color = const Color(0xFF484f58)
      ..strokeWidth = 1;

    double centerY = top + height / 2;
    double dashWidth = 10;
    double dashSpace = 5;
    double x = 0;
    while (x < size.width) {
      canvas.drawLine(
        Offset(x, centerY),
        Offset(x + dashWidth, centerY),
        centerPaint,
      );
      x += dashWidth + dashSpace;
    }
  }

  @override
  bool shouldRepaint(covariant ZonePainter oldDelegate) {
    return progress != oldDelegate.progress ||
        inZone != oldDelegate.inZone ||
        completed != oldDelegate.completed;
  }
}

/// Particle for celebration effect
class Particle {
  double x, y;
  double vx, vy;
  Color color;
  double size;
  double life = 1.0;

  Particle({
    required this.x,
    required this.y,
    required this.vx,
    required this.vy,
    required this.color,
    required this.size,
  });

  void update() {
    x += vx;
    y += vy;
    vy -= 0.001; // gravity
    life -= 0.02;
  }
}

// ============================================================================
// PLOTTER PAGE
// ============================================================================

class PlotterPage extends StatefulWidget {
  const PlotterPage({super.key});

  @override
  State<PlotterPage> createState() => _PlotterPageState();
}

class _PlotterPageState extends State<PlotterPage> {
  final BleDataService _ble = BleDataService();

  static const int maxPoints = 500;
  static const double displaySeconds = 10.0;
  static const double emaAlpha = 0.15;

  final Queue<DataPoint> _rawData = Queue();
  final Queue<DataPoint> _smoothData = Queue();

  double? _emaValue;
  double? _lastRaw;
  DateTime? _startTime;

  int _currentHz = 0;
  Timer? _hzTimer;

  bool _isConnected = false;

  @override
  void initState() {
    super.initState();
    _initListeners();
    _startHzTimer();
  }

  void _startHzTimer() {
    _hzTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (mounted) {
        setState(() {
          _currentHz = _ble.packetsPerSecond;
        });
      }
    });
  }

  void _initListeners() {
    _ble.connectionStream.listen((status) {
      if (mounted) {
        setState(() {
          _isConnected = _ble.isConnected;
        });
      }
    });

    _ble.rawDataStream.listen((value) {
      _handleNewValue(value);
    });

    _isConnected = _ble.isConnected;
  }

  void _handleNewValue(double value) {
    _startTime ??= DateTime.now();

    double t = DateTime.now().difference(_startTime!).inMilliseconds / 1000.0;

    _rawData.add(DataPoint(t, value));
    while (_rawData.length > maxPoints) {
      _rawData.removeFirst();
    }

    if (_emaValue == null) {
      _emaValue = value;
    } else {
      _emaValue = emaAlpha * value + (1 - emaAlpha) * _emaValue!;
    }

    _smoothData.add(DataPoint(t, _emaValue!));
    while (_smoothData.length > maxPoints) {
      _smoothData.removeFirst();
    }

    _lastRaw = value;

    if (mounted) {
      setState(() {});
    }
  }

  @override
  void dispose() {
    _hzTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0d1117),
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: _buildChart(),
              ),
            ),
            _buildStatsBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    Color statusColor = _isConnected
        ? const Color(0xFF3fb950)
        : const Color(0xFFf85149);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: const BoxDecoration(
        color: Color(0xFF161b22),
        border: Border(bottom: BorderSide(color: Color(0xFF30363d))),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back, color: Color(0xFF8b949e)),
            onPressed: () => Navigator.pop(context),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'Live Plotter',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFFf0f6fc),
              ),
            ),
          ),
          Icon(
            _isConnected ? Icons.bluetooth_connected : Icons.bluetooth_disabled,
            color: statusColor,
            size: 18,
          ),
          const SizedBox(width: 6),
          Text(
            _isConnected ? 'OK' : 'Lost',
            style: TextStyle(color: statusColor, fontSize: 12),
          ),
        ],
      ),
    );
  }

  Widget _buildChart() {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF161b22),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF30363d)),
      ),
      child: Stack(
        children: [
          if (_emaValue != null)
            Center(
              child: Text(
                _emaValue!.toStringAsFixed(0),
                style: TextStyle(
                  fontSize: 72,
                  fontWeight: FontWeight.bold,
                  color: const Color(0xFF58a6ff).withOpacity(0.1),
                  fontFamily: 'monospace',
                ),
              ),
            ),
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: CustomPaint(
              painter: ChartPainter(
                rawData: _rawData.toList(),
                smoothData: _smoothData.toList(),
                displaySeconds: displaySeconds,
              ),
              size: Size.infinite,
            ),
          ),
          Positioned(
            top: 10,
            left: 10,
            child: Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF21262d).withOpacity(0.9),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _legendItem('Raw', const Color(0xFFf85149)),
                  const SizedBox(height: 2),
                  _legendItem('Filtered', const Color(0xFF58a6ff)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _legendItem(String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 14,
          height: 2,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(1),
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(color: Color(0xFF8b949e), fontSize: 10),
        ),
      ],
    );
  }

  Widget _buildStatsBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        color: Color(0xFF161b22),
        border: Border(top: BorderSide(color: Color(0xFF30363d))),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _statItem('Hz', '$_currentHz', const Color(0xFF3fb950)),
          _statItem(
            'Raw',
            _lastRaw?.toStringAsFixed(0) ?? '--',
            const Color(0xFFf85149),
          ),
          _statItem(
            'Filtered',
            _emaValue?.toStringAsFixed(0) ?? '--',
            const Color(0xFF58a6ff),
          ),
          _statItem(
            'Norm',
            '${(_ble.normalizedForce * 100).toStringAsFixed(0)}%',
            const Color(0xFFd29922),
          ),
        ],
      ),
    );
  }

  Widget _statItem(String label, String value, Color valueColor) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: const TextStyle(color: Color(0xFF8b949e), fontSize: 10),
        ),
        Text(
          value,
          style: TextStyle(
            color: valueColor,
            fontSize: 14,
            fontWeight: FontWeight.bold,
            fontFamily: 'monospace',
          ),
        ),
      ],
    );
  }
}

/// Custom painter for the chart
class ChartPainter extends CustomPainter {
  final List<DataPoint> rawData;
  final List<DataPoint> smoothData;
  final double displaySeconds;

  ChartPainter({
    required this.rawData,
    required this.smoothData,
    required this.displaySeconds,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (rawData.isEmpty) return;

    const double padding = 36;
    final Rect chartArea = Rect.fromLTWH(
      padding,
      padding / 2,
      size.width - padding - 8,
      size.height - padding,
    );

    double currentTime = rawData.isNotEmpty ? rawData.last.time : 0;
    double minTime = currentTime - displaySeconds;

    List<DataPoint> visibleRaw = rawData
        .where((p) => p.time >= minTime)
        .toList();
    List<DataPoint> visibleSmooth = smoothData
        .where((p) => p.time >= minTime)
        .toList();

    if (visibleRaw.isEmpty) return;

    double minVal = double.infinity;
    double maxVal = double.negativeInfinity;
    for (var p in visibleRaw) {
      if (p.value < minVal) minVal = p.value;
      if (p.value > maxVal) maxVal = p.value;
    }

    double valueRange = maxVal - minVal;
    double margin = max(valueRange * 0.2, 1000);
    minVal -= margin;
    maxVal += margin;

    _drawGrid(canvas, chartArea, minTime, currentTime, minVal, maxVal);

    Offset toScreen(DataPoint p) {
      double x =
          chartArea.left +
          ((p.time - minTime) / displaySeconds) * chartArea.width;
      double y =
          chartArea.bottom -
          ((p.value - minVal) / (maxVal - minVal)) * chartArea.height;
      return Offset(x, y.clamp(chartArea.top, chartArea.bottom));
    }

    if (visibleRaw.length > 1) {
      final rawPaint = Paint()
        ..color = const Color(0xFFf85149).withOpacity(0.6)
        ..strokeWidth = 1.5
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;

      final rawPath = Path();
      rawPath.moveTo(
        toScreen(visibleRaw.first).dx,
        toScreen(visibleRaw.first).dy,
      );
      for (int i = 1; i < visibleRaw.length; i++) {
        rawPath.lineTo(toScreen(visibleRaw[i]).dx, toScreen(visibleRaw[i]).dy);
      }
      canvas.drawPath(rawPath, rawPaint);
    }

    if (visibleSmooth.length > 1) {
      final glowPaint = Paint()
        ..color = const Color(0xFF58a6ff).withOpacity(0.2)
        ..strokeWidth = 8
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;

      final glowPath = Path();
      glowPath.moveTo(
        toScreen(visibleSmooth.first).dx,
        toScreen(visibleSmooth.first).dy,
      );
      for (int i = 1; i < visibleSmooth.length; i++) {
        glowPath.lineTo(
          toScreen(visibleSmooth[i]).dx,
          toScreen(visibleSmooth[i]).dy,
        );
      }
      canvas.drawPath(glowPath, glowPaint);
    }

    if (visibleSmooth.length > 1) {
      final smoothPaint = Paint()
        ..color = const Color(0xFF58a6ff)
        ..strokeWidth = 3
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;

      final smoothPath = Path();
      smoothPath.moveTo(
        toScreen(visibleSmooth.first).dx,
        toScreen(visibleSmooth.first).dy,
      );
      for (int i = 1; i < visibleSmooth.length; i++) {
        smoothPath.lineTo(
          toScreen(visibleSmooth[i]).dx,
          toScreen(visibleSmooth[i]).dy,
        );
      }
      canvas.drawPath(smoothPath, smoothPaint);
    }
  }

  void _drawGrid(
    Canvas canvas,
    Rect area,
    double minTime,
    double maxTime,
    double minVal,
    double maxVal,
  ) {
    final gridPaint = Paint()
      ..color = const Color(0xFF30363d).withOpacity(0.5)
      ..strokeWidth = 1;

    final textStyle = TextStyle(color: const Color(0xFF8b949e), fontSize: 9);

    for (int i = 0; i <= 5; i++) {
      double x = area.left + (i / 5) * area.width;
      canvas.drawLine(Offset(x, area.top), Offset(x, area.bottom), gridPaint);

      double t = (i / 5) * (maxTime - minTime) + minTime;
      if (t >= 0) {
        final tp = TextPainter(
          text: TextSpan(text: '${t.toStringAsFixed(1)}s', style: textStyle),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas, Offset(x - tp.width / 2, area.bottom + 3));
      }
    }

    for (int i = 0; i <= 4; i++) {
      double y = area.top + (i / 4) * area.height;
      canvas.drawLine(Offset(area.left, y), Offset(area.right, y), gridPaint);

      double v = maxVal - (i / 4) * (maxVal - minVal);
      String label;
      if (v.abs() >= 1000000) {
        label = '${(v / 1000000).toStringAsFixed(1)}M';
      } else if (v.abs() >= 1000) {
        label = '${(v / 1000).toStringAsFixed(0)}K';
      } else {
        label = v.toStringAsFixed(0);
      }
      final tp = TextPainter(
        text: TextSpan(text: label, style: textStyle),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(area.left - tp.width - 4, y - tp.height / 2));
    }
  }

  @override
  bool shouldRepaint(covariant ChartPainter oldDelegate) {
    return rawData.length != oldDelegate.rawData.length ||
        smoothData.length != oldDelegate.smoothData.length;
  }
}
