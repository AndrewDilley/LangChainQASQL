function submitQuestion() {
    const question = document.getElementById('question').value;
    const responseDiv = document.getElementById('response');

    fetch('/ask', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: question})
    })
    .then(response => response.json())
    .then(data => {
        responseDiv.innerHTML = '';
        data.steps.forEach(step => {
            responseDiv.innerHTML += `<strong>${step.type}:</strong><br>${step.content}<br><br>`;
        });
        responseDiv.innerHTML += `<hr><strong>Final Answer:</strong><br>${data.final_answer}`;
    })
    .catch(error => {
        responseDiv.innerHTML = `Error: ${error}`;
    });
}
