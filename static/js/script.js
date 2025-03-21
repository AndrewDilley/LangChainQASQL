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

function renderChart(data) {
    // Show chart container
    document.getElementById('chartContainer').style.display = 'block';

    // Destroy any existing chart instance if necessary
    if(window.myChart instanceof Chart) {
        window.myChart.destroy();
    }

    const ctx = document.getElementById('resultChart').getContext('2d');
    window.myChart = new Chart(ctx, {
        type: 'bar',  // Adjust this type as needed (e.g., 'line', 'pie')
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Work Orders',
                data: data.values,
                backgroundColor: 'rgba(0, 123, 255, 0.5)',
                borderColor: 'rgba(0, 123, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}
