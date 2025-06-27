let barChart, expenseChart;

// Load data when page opens
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('date').valueAsDate = new Date();
    loadTransactions();
    loadStats();
});

// Add transaction
function addTransaction() {
    const transaction = {
        date: document.getElementById('date').value,
        description: document.getElementById('description').value,
        amount: parseFloat(document.getElementById('amount').value),
        category: document.getElementById('category').value,
        type: document.getElementById('type').value
    };

    if (!transaction.description || isNaN(transaction.amount)) {
        alert('Please fill description and amount!');
        return;
    }

    fetch('/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transaction)
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to add');
        return response.json();
    })
    .then(() => {
        loadTransactions();
        loadStats();
        document.getElementById('description').value = '';
        document.getElementById('amount').value = '';
    })
    .catch(err => alert('Error: ' + err.message));
}

// Set budget
function setBudget() {
    const budget = {
        category: document.getElementById('budget-category').value,
        amount: parseFloat(document.getElementById('budget-amount').value)
    };

    if (!budget.category || isNaN(budget.amount)) {
        alert('Please select category and enter amount!');
        return;
    }

    fetch('/budget', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(budget)
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to set budget');
        return response.json();
    })
    .then(() => {
        loadStats();
        document.getElementById('budget-amount').value = '';
        document.getElementById('budget-status').innerHTML = 
            `<div class="alert-success">Budget set for ${budget.category}</div>`;
    })
    .catch(err => {
        document.getElementById('budget-status').innerHTML = 
            `<div class="alert-error">Error: ${err.message}</div>`;
    });
}

// Delete transaction
function deleteTransaction(id) {
    if (confirm('Delete this transaction?')) {
        fetch(`/delete/${id}`, { method: 'DELETE' })
        .then(response => {
            if (!response.ok) throw new Error('Failed to delete');
            loadTransactions();
            loadStats();
        })
        .catch(err => alert('Error: ' + err.message));
    }
}

// Load transactions
function loadTransactions() {
    fetch('/transactions')
    .then(response => {
        if (!response.ok) throw new Error('Network error');
        return response.json();
    })
    .then(data => {
        const tbody = document.querySelector('#transactions tbody');
        tbody.innerHTML = '';
        
        data.forEach(transaction => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${transaction.date}</td>
                <td>${transaction.description}</td>
                <td>₹${transaction.amount.toFixed(2)}</td>
                <td>${transaction.category}</td>
                <td>${transaction.type}</td>
                <td><button onclick="deleteTransaction(${transaction.id})" class="btn danger">Delete</button></td>
            `;
            tbody.appendChild(row);
        });
    })
    .catch(err => console.error('Error:', err));
}

// Load stats and update charts
function loadStats() {
    fetch('/stats')
    .then(response => {
        if (!response.ok) throw new Error('Network error');
        return response.json();
    })
    .then(data => {
        // Update stats cards
        document.getElementById('total-income').textContent = data.income.toFixed(2);
        document.getElementById('total-expense').textContent = data.expense.toFixed(2);
        document.getElementById('net-savings').textContent = data.net_savings.toFixed(2);
        document.getElementById('savings-rate').textContent = data.savings_rate.toFixed(1);
        
        // Update charts
        updateCharts(data);
        
        // Update budget status
        updateBudgetStatus(data);
    })
    .catch(err => console.error('Error:', err));
}

// Update charts
function updateCharts(data) {
    const barCtx = document.getElementById('barChart').getContext('2d');
    const expenseCtx = document.getElementById('expenseChart').getContext('2d');

    // Destroy old charts if they exist
    if (barChart) barChart.destroy();
    if (expenseChart) expenseChart.destroy();

    // Income vs Expense Bar Chart
    barChart = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels: ['Income', 'Expenses'],
            datasets: [{
                label: 'Amount',
                data: [data.income, data.expense],
                backgroundColor: ['#4CAF50', '#F44336'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });

    // Expense Breakdown Pie Chart
    expenseChart = new Chart(expenseCtx, {
        type: 'pie',
        data: {
            labels: data.categories.map(item => item.category),
            datasets: [{
                data: data.categories.map(item => item.total),
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
                    '#FF9F40', '#8AC24A', '#607D8B', '#9C27B0', '#E91E63',
                    '#00BCD4', '#CDDC39'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}
    // Delete budget
function deleteBudget() {
    const category = document.getElementById('budget-category').value;
    
    if (!category) {
        alert('Please select a category to delete!');
        return;
    }

    if (confirm(`Delete budget for ${category}?`)) {
        fetch(`/budget/${category}`, {
            method: 'DELETE',
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to delete budget');
            return response.json();
        })
        .then(() => {
            loadStats();
            document.getElementById('budget-status').innerHTML = 
                `<div class="alert-success">Budget for ${category} deleted</div>`;
        })
        .catch(err => {
            document.getElementById('budget-status').innerHTML = 
                `<div class="alert-error">Error: ${err.message}</div>`;
        });
    }
}

function updateBudgetStatus(data) {
    const budgetStatus = document.getElementById('budget-status');
    budgetStatus.innerHTML = '<h4>Budget Status</h4>';
    
    if (data.budgets.length === 0) {
        budgetStatus.innerHTML += '<p>No budgets set for this month</p>';
        return;
    }
    
    data.budgets.forEach(budget => {
        const categoryExpense = data.categories.find(c => c.category === budget.category);
        const spent = categoryExpense ? categoryExpense.total : 0;
        const percentage = (spent / budget.amount) * 100;
        const isOverBudget = spent > budget.amount;
        
        budgetStatus.innerHTML += `
            <div class="budget-item">
                <span>${budget.category}</span>
                <span>₹${spent.toFixed(2)} / ₹${budget.amount.toFixed(2)}</span>
                <button onclick="deleteSingleBudget('${budget.category}')" class="btn danger small">Delete</button>
            </div>
            <div class="budget-progress">
                <div class="budget-progress-bar ${isOverBudget ? 'over-budget' : 'under-budget'}" 
                     style="width: ${Math.min(percentage, 100)}%"></div>
            </div>
        `;
    });
}

// Add this new function to delete individual budgets
function deleteSingleBudget(category) {
    if (confirm(`Delete budget for ${category}?`)) {
        fetch(`/budget/${category}`, {
            method: 'DELETE',
        })
        .then(response => {
            if (!response.ok) throw new Error('Failed to delete budget');
            loadStats();
        })
        .catch(err => {
            document.getElementById('budget-status').innerHTML += 
                `<div class="alert-error">Error deleting ${category} budget: ${err.message}</div>`;
        });
    }
}
