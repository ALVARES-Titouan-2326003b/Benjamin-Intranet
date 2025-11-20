console.log("vue_financiere.js chargé ✅");

function initFinanceCharts(config) {
    const { fraisEngages, fraisPayes, fraisRestants, totalEstime } = config;

    const barCanvas = document.getElementById("barChart");

    if (!barCanvas || typeof Chart === "undefined") {
        console.warn("Chart.js non chargé ou canvas introuvable.");
        return;
    }

    const ctx = barCanvas.getContext("2d");

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Engagés", "Payés", "Restants", "Total estimé"],
            datasets: [
                {
                    label: "Montants (€)",
                    data: [fraisEngages, fraisPayes, fraisRestants, totalEstime],
                    backgroundColor: [
                        "rgba(54, 162, 235, 0.6)",
                        "rgba(75, 192, 192, 0.6)",
                        "rgba(255, 159, 64, 0.6)",
                        "rgba(153, 102, 255, 0.6)"
                    ],
                    borderColor: [
                        "rgba(54, 162, 235, 1)",
                        "rgba(75, 192, 192, 1)",
                        "rgba(255, 159, 64, 1)",
                        "rgba(153, 102, 255, 1)"
                    ],
                    borderWidth: 1.5
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            animation: {
                duration: 900,
                easing: "easeOutCubic"
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            const value = ctx.parsed.y;
                            return value.toLocaleString("fr-FR", {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            }) + " €";
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        font: { size: 11 },
                        callback: function (value) {
                            return value.toLocaleString("fr-FR");
                        }
                    }
                },
                x: {
                    ticks: {
                        font: { size: 11 }
                    }
                }
            }
        }
    });
}
