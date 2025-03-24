function submitQuestion() {
    const question = document.getElementById('question').value;
    const visualize = document.getElementById('visualize').checked;
    const responseDiv = document.getElementById('response');

    fetch('/ask', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: question, visualize: visualize})
    })
    .then(response => response.json())
    .then(data => {
        responseDiv.innerHTML = '';
        data.steps.forEach(step => {
            responseDiv.innerHTML += `<strong>${step.type}:</strong><br>${step.content}<br><br>`;
        });
        responseDiv.innerHTML += `<hr><strong>Final Answer:</strong><br>${data.final_answer}`;

        // Check if visualization data is available
        if(data.visualizationData) {
            renderChart(data.visualizationData);
        } else {
            // Hide the chart container if no visualization data is present
            document.getElementById('chartContainer').style.display = 'none';
        }
    })
    .catch(error => {
        responseDiv.innerHTML = `Error: ${error}`;
    });
}

// function renderChart(data) {
//     // Show chart container
//     document.getElementById('chartContainer').style.display = 'block';

//     // Destroy any existing chart instance if necessary
//     if(window.myChart instanceof Chart) {
//         window.myChart.destroy();
//     }

//     const ctx = document.getElementById('resultChart').getContext('2d');
//     window.myChart = new Chart(ctx, {
//         type: 'bar',  // Adjust this type as needed (e.g., 'line', 'pie')
//         data: {
//             labels: data.labels,
//             datasets: [{
//                 label: 'Work Orders',
//                 data: data.values,
//                 backgroundColor: 'rgba(0, 123, 255, 0.5)',
//                 borderColor: 'rgba(0, 123, 255, 1)',
//                 borderWidth: 1
//             }]
//         },
//         options: {
//             scales: {
//                 y: {
//                     beginAtZero: true
//                 }
//             }
//         }
//     });
// }


function renderChart(data) {
    // Show chart container
    document.getElementById('chartContainer').style.display = 'block';

    // Destroy any existing chart instance if necessary
    if (window.myChart instanceof Chart) {
        window.myChart.destroy();
    }

    const ctx = document.getElementById('resultChart').getContext('2d');

    let chartData;
    // Check if multi-series data exists
    if (data.datasets) {
        chartData = {
            labels: data.labels,
            datasets: data.datasets.map((dataset, index) => {
                // Provide default colors if none are specified
                const defaultColors = [
                    'rgba(0, 123, 255, 0.5)',
                    'rgba(255, 99, 132, 0.5)',
                    'rgba(54, 162, 235, 0.5)',
                    'rgba(255, 206, 86, 0.5)',
                    'rgba(75, 192, 192, 0.5)'
                ];
                const defaultBorderColors = [
                    'rgba(0, 123, 255, 1)',
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)'
                ];
                return {
                    label: dataset.label,
                    data: dataset.data,
                    backgroundColor: dataset.backgroundColor || defaultColors[index % defaultColors.length],
                    borderColor: dataset.borderColor || defaultBorderColors[index % defaultBorderColors.length],
                    borderWidth: 1
                };
            })
        };
    } else {
        // Fallback to single-series chart if no multi-series data is provided
        chartData = {
            labels: data.labels,
            datasets: [{
                label: 'Work Orders',
                data: data.values,
                backgroundColor: 'rgba(0, 123, 255, 0.5)',
                borderColor: 'rgba(0, 123, 255, 1)',
                borderWidth: 1
            }]
        };
    }

    window.myChart = new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: true
                }
            }
        }
    });
}

