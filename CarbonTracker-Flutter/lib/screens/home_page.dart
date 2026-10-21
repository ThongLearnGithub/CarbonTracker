import 'package:flutter/material.dart';
import 'map.dart';

import '../services/api_service.dart';
import '../models/api_homepage.dart';
import '../models/api_wallet.dart';
import '../models/api_trip_stats.dart';

class HomePage extends StatefulWidget {
  final int userId;
  final void Function(int)? onTabSelected;
  final VoidCallback? onTripSaved;
  const HomePage({
    super.key,
    required this.userId,
    this.onTabSelected,
    this.onTripSaved,
  });

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final ApiService _api = ApiService();

  late Future<_HomeData> _futureData;

  @override
  void initState() {
    super.initState();
    _futureData = _loadData();
  }

  Future<_HomeData> _loadData() async {
    final home = await _api.fetchHomePageSummary(widget.userId);
    final wallet = await _api.fetchWalletSummary(widget.userId);
    final stats = await _api.fetchTripStats(widget.userId);

    return _HomeData(home: home, wallet: wallet, stats: stats);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        automaticallyImplyLeading: false,
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          'Carbon Tracker',
          style: TextStyle(
            color: Color(0xFF4CAF50),
            fontSize: 30,
            fontWeight: FontWeight.bold,
          ),
        ),
        centerTitle: false,
      ),
      body: FutureBuilder<_HomeData>(
        future: _futureData,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Center(
              child: Text(
                'Failed to load homepage: ${snapshot.error}',
                style: const TextStyle(color: Colors.red),
              ),
            );
          }

          final data = snapshot.data!;
          final home = data.home;
          final wallet = data.wallet;
          final stats = data.stats;

          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _BalanceCard(
                  balance: wallet.balanceCredits,
                  subtitle: '+${wallet.creditsThisWeek} this week',
                ),
                const SizedBox(height: 16),

                Row(
                  children: [
                    Expanded(
                      child: _StatCard(
                        title: 'CO₂ Saved',
                        value: '${home.co2SavedKg.toStringAsFixed(2)} kg',
                        sub: 'This month',
                        valueColor: const Color(0xFF4CAF50),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _StatCard(
                        title: 'Distance',
                        value: '${home.distanceKm.toStringAsFixed(2)} km',
                        sub: 'This month',
                        valueColor: const Color(0xFF30A0FB),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF4CAF50),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    onPressed: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (context) => MapScreen(
                            userId: widget.userId,
                            onTripSaved: widget.onTripSaved,
                          ),
                        ),
                      );
                    },

                    icon: const Icon(Icons.play_circle_fill,
                        color: Colors.white),
                    label: const Text('Start Tracking',
                        style: TextStyle(fontSize: 16)),
                  ),
                ),
                const SizedBox(height: 20),

                Row(
                  children: [
                    Expanded(
                      child: _QuickAction(
                        title: 'Trip History',
                        icon: Icons.access_time_rounded,
                        iconColor: const Color(0xFF4CAF50),
                        onTap: () => widget.onTabSelected?.call(1),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _QuickAction(
                        title: 'Wallet',
                        icon: Icons.account_balance_wallet_rounded,
                        iconColor: const Color(0xFF30A0FB),
                        onTap: () => widget.onTabSelected?.call(2),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _QuickAction(
                        title: 'Vouchers',
                        icon: Icons.card_giftcard,
                        iconColor: const Color(0xFF4CAF50),
                        onTap: () => widget.onTabSelected?.call(3),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _QuickAction(
                        title: 'AI Tips',
                        icon: Icons.adb_outlined,
                        iconColor: const Color(0xFF30A0FB),
                        onTap: () {},
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 24),

                _ChartCard(series: stats.daily),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _HomeData {
  final HomePageSummary home;
  final ApiWalletSummary wallet;
  final TripStats stats;

  _HomeData({required this.home, required this.wallet, required this.stats});
}

class _BalanceCard extends StatelessWidget {
  final int balance;
  final String subtitle;

  const _BalanceCard({required this.balance, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF00AD14), Color(0xFF157AC3)],
          begin: Alignment.topLeft,
          end: Alignment.topRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 8,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Carbon Credits Balance',
              style: TextStyle(color: Colors.white, fontSize: 22)),
          const SizedBox(height: 8),
          Text(
            _fmt(balance),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 32,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          Text(subtitle, style: const TextStyle(color: Colors.white70)),
        ],
      ),
    );
  }

  String _fmt(int n) => n.toString().replaceAllMapped(
      RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]},');
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final String sub;
  final Color valueColor;

  const _StatCard({
    required this.title,
    required this.value,
    required this.sub,
    required this.valueColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 125,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.shade300, width: 1),
      ),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: Colors.grey.shade500,
              fontSize: 13,
              fontWeight: FontWeight.w400,
            ),
          ),
          const Spacer(),
          Text(
            value,
            style: TextStyle(
              color: valueColor,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            sub,
            style: TextStyle(
              color: Colors.grey.shade500,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _QuickAction extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color iconColor;
  final VoidCallback? onTap;

  const _QuickAction({
    required this.title,
    required this.icon,
    required this.iconColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Card(
        elevation: 2,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 14),
          child: Column(
            children: [
              Icon(icon, color: iconColor, size: 30),
              const SizedBox(height: 8),
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  color: Colors.black,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ChartCard extends StatelessWidget {
  final List<SeriesPoint> series;

  const _ChartCard({required this.series});

  @override
  Widget build(BuildContext context) {
    final values =
    series.map((e) => e.credits.toDouble()).toList(growable: false);
    final labels =
    series.map((e) => e.label).toList(growable: false);

    return Card(
      color: Colors.white,
      surfaceTintColor: Colors.white,
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Daily Credits Earned',
              style: TextStyle(
                color: Colors.black,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            _MiniBarChart(values: values, labels: labels),
          ],
        ),
      ),
    );
  }
}


class _MiniBarChart extends StatelessWidget {
  final List<double> values;
  final List<String> labels;

  const _MiniBarChart({required this.values, required this.labels});

  @override
  Widget build(BuildContext context) {
    if (values.isEmpty) {
      return const SizedBox(
        height: 120,
        child: Center(child: Text('No data')),
      );
    }

    final maxVal = values.reduce((a, b) => a > b ? a : b) * 1.2;

    return SizedBox(
      height: 160,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: List.generate(values.length, (i) {
          final h = (values[i] / maxVal) * 100;
          return Column(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              Container(
                height: h.clamp(6, 100),
                width: 18,
                decoration: BoxDecoration(
                  color: const Color(0xFF4CAF50),
                  borderRadius: BorderRadius.circular(5),
                ),
              ),
              const SizedBox(height: 6),
              Text(
                labels[i],
                style: TextStyle(
                  color: Colors.grey.shade600,
                  fontSize: 12,
                ),
              ),
            ],
          );
        }),
      ),
    );
  }
}
