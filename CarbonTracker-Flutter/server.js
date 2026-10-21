const express = require("express");
const swaggerUi = require("swagger-ui-express");
const YAML = require("yamljs");

const app = express();
const swaggerDocument = YAML.load("./swagger.yaml");

app.use(express.json());
app.use("/api-docs", swaggerUi.serve, swaggerUi.setup(swaggerDocument));

// Mock data đơn giản để test API
const emissions = [
  { date: "2025-11-07", category: "Transport", value: 12.5 },
  { date: "2025-11-06", category: "Electricity", value: 7.8 },
];

// Endpoint thật để test
app.get("/api/emissions", (req, res) => {
  res.json(emissions);
});

app.post("/api/emissions", (req, res) => {
  emissions.push(req.body);
  res.status(201).json({ message: "Đã thêm bản ghi thành công!" });
});

app.get("/api/users/:id", (req, res) => {
  const user = [
  { id: 1, name: "Khoa Mai", email: "khoa@gmail.com" },
  { id: 2, name: "Khoa Mai", email: "khoa@gmail.com" },
  ];
  res.json(user);
});

app.listen(8080, () => {
  console.log("🚀 Swagger UI running at http://localhost:8080/api-docs");
});
