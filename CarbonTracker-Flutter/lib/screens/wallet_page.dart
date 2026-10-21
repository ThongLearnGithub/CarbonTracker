import 'package:flutter/material.dart';
import 'voucher_page.dart';
import '../services/api_service.dart';
import '../models/api_wallet.dart';

class WalletPage extends StatefulWidget {
  final int userId;
  final void Function(int)? onTabSelected;
  const WalletPage({
    Key? key,
    required this.userId,
    this.onTabSelected,
  }) : super(key: key);

  @override
  WalletPageState createState() => WalletPageState();
}

class WalletPageState extends State<WalletPage> {
  final ApiService _api = ApiService();
  late Future<ApiWalletSummary> _futureWallet;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    _futureWallet = _api.fetchWalletSummary(widget.userId);
  }

  void reloadData() {
    setState(() {
      _loadData();
    });
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
          'Wallet',
          style: TextStyle(
            color: Color(0xFF4CAF50),
            fontSize: 30,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 15),
            child: Icon(
              Icons.account_balance_wallet_rounded,
              color: Colors.grey,
            ),
          ),
        ],
      ),
      body: FutureBuilder<ApiWalletSummary>(
        future: _futureWallet,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (snapshot.hasError || !snapshot.hasData) {
            return Center(
              child: Text(
                'Failed to load wallet: ${snapshot.error}',
                style: const TextStyle(color: Colors.red),
                textAlign: TextAlign.center,
              ),
            );
          }

          final summary = snapshot.data!;

          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _BalanceCard(
                  balance: summary.balanceCredits,
                  subtitle: '+${summary.creditsThisWeek} this week',
                ),
                const SizedBox(height: 12),


                Row(
                  children: [
                    Expanded(
                      child: _MiniStatCard(
                        value: summary.creditsThisWeek.toString(),
                        caption: 'This Week',
                        valueColor: const Color(0xFF4CAF50),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _MiniStatCard(
                        value: summary.creditsThisMonth.toString(),
                        caption: 'This Month',
                        valueColor: const Color(0xFF30A0FB),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 14),


                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF30A0FB),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    onPressed: () async {
                      await Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => VoucherPage(userId: widget.userId),
                        ),
                      );
                      setState(() { // load lại wallet
                        _futureWallet = _api.fetchWalletSummary(widget.userId);
                      });
                    },
                    icon: const Icon(Icons.card_giftcard),
                    label: const Text('Redeem Vouchers'),
                  ),
                ),

                const SizedBox(height: 16),


                Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    border: Border.all(color: Colors.grey.shade300),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    children: [
                      Padding(
                        padding:
                        const EdgeInsets.fromLTRB(14, 12, 14, 10),
                        child: Row(
                          children: const [
                            Icon(
                              Icons.calendar_today_rounded,
                              size: 18,
                              color: Colors.black87,
                            ),
                            SizedBox(width: 8),
                            Text(
                              'Credit History',
                              style: TextStyle(
                                fontSize: 16,
                                color: Colors.black,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            Spacer(),
                          ],
                        ),
                      ),
                      const Divider(
                        height: 1,
                        color: Color(0xFFE0E0E0),
                      ),

                      if (summary.history.isEmpty)
                        const Padding(
                          padding: EdgeInsets.all(16.0),
                          child: Text(
                            'No credit history.',
                            style: TextStyle(color: Colors.grey),
                          ),
                        )
                      else
                        ..._buildHistoryWidgets(summary.history),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  List<Widget> _buildHistoryWidgets(
      List<ApiWalletHistoryItem> history) {
    final widgets = <Widget>[];

    for (int i = 0; i < history.length; i++) {
      final item = history[i];

      final bool isTrip =
          item.kind == 'trip_earned';
      final icon = isTrip
          ? Icons.calendar_today_rounded
          : Icons.card_giftcard;

      final status =
      item.amount >= 0 ? _HistoryStatus.earned : _HistoryStatus.redeemed;

      widgets.add(
        _HistoryItem(
          icon: icon,
          title: item.title,
          date: _formatDate(item.date),
          amount: item.amount,
          status: status,
        ),
      );

      if (i != history.length - 1) {
        widgets.add(const Divider(
          height: 1,
          color: Color(0xFFE0E0E0),
        ));
      }
    }

    widgets.add(const SizedBox(height: 6));
    return widgets;
  }

  String _formatDate(String iso) {
    try {
      final d = DateTime.parse(iso);
      const months = [
        'Jan',
        'Feb',
        'Mar',
        'Apr',
        'May',
        'Jun',
        'Jul',
        'Aug',
        'Sep',
        'Oct',
        'Nov',
        'Dec'
      ];
      final m = months[d.month - 1];
      return '$m ${d.day}, ${d.year}';
    } catch (_) {
      return iso;
    }
  }
}


class _BalanceCard extends StatelessWidget {
  final int balance;
  final String subtitle;
  const _BalanceCard({required this.balance, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 14),
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
          Row(
            children: const [
              Icon(
                Icons.account_balance_wallet_rounded,
                size: 22,
                color: Colors.white,
              ),
              SizedBox(width: 8),
              Flexible(
                child: Text(
                  'Carbon Credits Balance',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
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
          Text(
            subtitle,
            style: const TextStyle(color: Colors.white70),
          ),
        ],
      ),
    );
  }

  String _fmt(int n) => n.toString().replaceAllMapped(
    RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
        (m) => '${m[1]},',
  );
}

class _MiniStatCard extends StatelessWidget {
  final String value;
  final String caption;
  final Color valueColor;

  const _MiniStatCard({
    required this.value,
    required this.caption,
    this.valueColor = const Color(0xFF4CAF50),
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 90,
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(12),
      ),
      padding:
      const EdgeInsets.symmetric(horizontal: 15, vertical: 10),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            value,
            style: TextStyle(
              color: valueColor,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 4),
          Flexible(
            child: Text(
              caption,
              style: TextStyle(color: Colors.grey.shade600),
              textAlign: TextAlign.center,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

enum _HistoryStatus { earned, redeemed }

class _HistoryItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String date;
  final int amount;
  final _HistoryStatus status;

  const _HistoryItem({
    required this.icon,
    required this.title,
    required this.date,
    required this.amount,
    required this.status,
  });

  @override
  Widget build(BuildContext context) {
    final isEarned = status == _HistoryStatus.earned;
    final amountColor =
    isEarned ? const Color(0xFF4CAF50) : const Color(0xFFFE4848);
    final badgeColor =
    isEarned ? const Color(0xFFECF8F0) : const Color(0xFFFDEBEC);
    final badgeText = isEarned ? 'earned' : 'redeemed';
    final leadingBg =
    isEarned ? const Color(0xFFC9F6C3) : const Color(0xFFFFF0F0);
    final leadingIconColor =
    isEarned ? const Color(0xFF4CAF50) : const Color(0xFFFE4848);

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: leadingBg,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              icon,
              color: leadingIconColor,
              size: 20,
            ),
          ),
          const SizedBox(width: 10),


          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.black,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  date,
                  style: TextStyle(
                    color: Colors.grey.shade600,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),


          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                amount > 0 ? '+$amount' : '$amount',
                style: TextStyle(
                  color: amountColor,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: badgeColor,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  badgeText,
                  style: TextStyle(
                    color: amountColor,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
