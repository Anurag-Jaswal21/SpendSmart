const ctx = document.getElementById('monthlyChart').getContext('2d');
const myPieChart = new Chart(ctx, {
    type: 'pie',
    data: {
        labels: ['Income', 'Expenses', 'Savings'],
        datasets: [{
            data: [300, 150, 100],
            backgroundColor: ['#36A2EB', '#FF6384', '#FFCE56'],
            borderWidth: 1
        }]
    },
    options: {
        responsive: true
    }
});
