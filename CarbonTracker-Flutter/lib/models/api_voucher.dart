class ApiVoucher {
  final int id;
  final String title;
  final String description;
  final int credits;
  final String status;
  final String? category;
  final double rating;
  final String availability;

  ApiVoucher({
    required this.id,
    required this.title,
    required this.description,
    required this.credits,
    required this.status,
    this.category,
    required this.rating,
    required this.availability,
  });

  factory ApiVoucher.fromJson(Map<String, dynamic> json) {
    return ApiVoucher(
      id: json['id'] as int,
      title: json['title'] as String,
      description: json['description'] as String,
      credits: json['credits'] as int,
      status: json['status'] as String,
      category: json['category'] as String?,
      rating: (json['rating'] as num).toDouble(),
      availability: json['availability'] as String,
    );
  }
}
