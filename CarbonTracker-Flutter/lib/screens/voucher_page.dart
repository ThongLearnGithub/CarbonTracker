import 'package:flutter/material.dart';
import 'dart:math';

import 'my_voucher_page.dart';
import '../services/api_service.dart';
import '../models/api_voucher.dart';
import '../models/api_wallet.dart';

class VoucherPage extends StatefulWidget {
  final int userId;

  const VoucherPage({super.key, required this.userId});

  @override
  State<VoucherPage> createState() => _VoucherPageState();
}

String _generateVoucherCode() {
  final random = Random();
  final code = List.generate(6, (_) => random.nextInt(10)).join();
  return code;
}

class _VoucherPageState extends State<VoucherPage> {
  final ApiService _api = ApiService();

  String selectedCategory = "All";

  final List<String> categories = [
    "All",
    "Transport",
    "Shopping",
    "Green",
    "Charity",
  ];

  late Future<ApiWalletSummary> _futureWallet;
  late Future<List<ApiVoucher>> _futureVouchers;

  @override
  void initState() {
    super.initState();
    _futureWallet = _api.fetchWalletSummary(widget.userId);
    _futureVouchers = _api.fetchVouchers();
  }


  String _mapCategoryToTab(String? cat) {
    switch (cat?.toLowerCase()) {
      case 'transport':
        return 'Transport';
      case 'shopping':
        return 'Shopping';
      case 'green':
        return 'Green';
      case 'charity':
        return 'Charity';
      default:
        return 'All';
    }
  }

  IconData _iconForCategory(String? cat) {
    switch (cat?.toLowerCase()) {
      case 'transport':
        return Icons.directions_bus;
      case 'shopping':
        return Icons.local_cafe_outlined;
      case 'green':
        return Icons.eco_outlined;
      case 'charity':
        return Icons.water_drop_outlined;
      default:
        return Icons.card_giftcard_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        automaticallyImplyLeading: true,
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        title: FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: const Text(
            "Voucher Marketplace",
            style: TextStyle(
              color: Color(0xFF4CAF50),
              fontSize: 30,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 15),
            child: Icon(Icons.card_giftcard_outlined, color: Colors.grey),
          )
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
              ),
            );
          }

          final wallet = snapshot.data!;

          return Column(
            children: [
              Container(
                margin: const EdgeInsets.all(12),
                padding:
                const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFF66B34A), Color(0xFF7FF4E6)],
                  ),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          "Available Credits",
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          _fmt(wallet.balanceCredits),
                          style: const TextStyle(
                            fontSize: 24,
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                    const Icon(Icons.card_giftcard_outlined,
                        color: Colors.white, size: 30),
                  ],
                ),
              ),

              // Category Tab
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Row(
                  children: categories.map((cat) {
                    final bool isSelected = selectedCategory == cat;
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: ChoiceChip(
                        label: Text(cat),
                        selected: isSelected,
                        selectedColor: const Color(0xFF4CAF50),
                        backgroundColor: Colors.white,
                        labelStyle: TextStyle(
                          color: isSelected ? Colors.white : Colors.black87,
                        ),
                        onSelected: (_) {
                          setState(() => selectedCategory = cat);
                        },
                      ),
                    );
                  }).toList(),
                ),
              ),

              const SizedBox(height: 8),

              // Voucher list
              Expanded(
                child: FutureBuilder<List<ApiVoucher>>(
                  future: _futureVouchers,
                  builder: (context, snapshot) {
                    if (snapshot.connectionState ==
                        ConnectionState.waiting) {
                      return const Center(
                          child: CircularProgressIndicator());
                    }
                    if (snapshot.hasError) {
                      return Center(
                        child: Text('Error: ${snapshot.error}'),
                      );
                    }

                    final all = snapshot.data ?? [];

                    // filter voucher
                    final filteredByCategory = selectedCategory == "All"
                        ? all
                        : all
                        .where((v) =>
                    _mapCategoryToTab(v.category) ==
                        selectedCategory)
                        .toList();

                    final visible = filteredByCategory
                        .where((v) =>
                    v.status.toLowerCase() != 'redeemed')
                        .toList();

                    return ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: visible.length + 1, // +1 cho How it works
                      itemBuilder: (context, index) {
                        if (index < visible.length) {
                          final v = visible[index];
                          return _buildVoucherCard(
                            v,
                            wallet.balanceCredits,
                          );
                        } else {
                          return _buildHowItWorksBox();
                        }
                      },
                    );

                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  // Voucher card
  Widget _buildVoucherCard(ApiVoucher v, int balanceCredits) {
    final icon = _iconForCategory(v.category);
    final bool isExpired = v.status.toLowerCase() == 'expired';

    final bool hasEnoughCredits = balanceCredits >= v.credits;
    final bool canRedeem = !isExpired && hasEnoughCredits;

    return Container(
      margin: const EdgeInsets.only(bottom: 15),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade400),
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        boxShadow: [
          BoxShadow(
            color: Colors.grey.withOpacity(0.12),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF66B34A), Color(0xFF7CFFF0)],
              ),
              borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            child: Stack(
              alignment: Alignment.center,
              children: [
                Align(
                  alignment: Alignment.center,
                  child: Icon(
                    icon,
                    color: const Color(0xFF4CAF50),
                    size: 36,
                  ),
                ),
                Align(
                  alignment: Alignment.topRight,
                  child: Container(
                    padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF4CAF50),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      "${v.credits} credits",
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),


          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  v.title,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    color: Colors.black54,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  v.description,
                  style: const TextStyle(color: Colors.grey, fontSize: 13),
                ),
                const SizedBox(height: 10),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.star,
                            color: Colors.orange, size: 18),
                        const SizedBox(width: 4),
                        Text(
                          v.rating.toStringAsFixed(1),
                          style: const TextStyle(
                              fontSize: 14, color: Colors.black54),
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        const Icon(Icons.access_time, size: 16),
                        const SizedBox(width: 4),
                        Text(
                          v.availability,
                          style: TextStyle(
                            color: isExpired ? Colors.red : Colors.grey,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    )
                  ],
                ),
                const SizedBox(height: 14),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: !canRedeem
                        ? () {
                      final msg = isExpired
                          ? 'This voucher is expired.'
                          : 'Not enough credits.';
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(msg)),
                      );
                    }
                        : () async {
                      try {
                        final redeemed =
                        await _api.redeemVoucher(v.id, widget.userId);

                        // Lưu vào MyVoucher
                        final newVoucher = Voucher(
                          title: redeemed.title,
                          description: redeemed.description,
                          extraInfo: redeemed.availability,
                          icon:
                          _iconForCategory(redeemed.category),
                          status: VoucherStatus.pending,
                          code: _generateVoucherCode(),
                          credits: redeemed.credits,
                        );
                        myVoucherStore.add(newVoucher);

                        // load lại UI
                        setState(() {
                          _futureVouchers = _api.fetchVouchers();
                          _futureWallet = _api.fetchWalletSummary(widget.userId);
                        });

                        ScaffoldMessenger.of(context)
                            .showSnackBar(
                          SnackBar(
                            content: Text(
                              'Redeemed "${redeemed.title}". Check it in My Voucher.',
                            ),
                            behavior:
                            SnackBarBehavior.floating,
                          ),
                        );
                      } catch (e) {
                        ScaffoldMessenger.of(context)
                            .showSnackBar(
                          SnackBar(
                            content:
                            Text('Redeem error: $e'),
                          ),
                        );
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: canRedeem
                          ? const Color(0xFF4CAF50)
                          : Colors.grey.shade400,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      padding:
                      const EdgeInsets.symmetric(vertical: 12),
                    ),
                    child: const Text(
                      "Redeem",
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildHowItWorksBox() {
    return Container(
      margin: const EdgeInsets.only(top: 4, bottom: 20),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFE8F8E5),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFBDE5B2)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Icon(Icons.info_outline,
              color: Color(0xFF21A366), size: 24),
          SizedBox(width: 10),
          Expanded(
            child: Text(
              "💡 How it works\nEarn credits by choosing eco-friendly transport. "
                  "Redeem vouchers to save money and support sustainability!",
              style: TextStyle(
                color: Color(0xFF2E7D32),
                fontSize: 14,
                height: 1.4,
              ),
            ),
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
