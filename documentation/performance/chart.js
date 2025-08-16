// Performance data processing and chart creation

async function loadPerformanceData() {
  try {
    const response = await fetch('performance/performance_overall.yaml');
    const yamlText = await response.text();
    
    // Parse YAML content (simple parsing for this structure)
    const lines = yamlText.split('\n');
    const models = [];
    let currentModel = null;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      if (line.startsWith('- name:')) {
        if (currentModel) {
          models.push(currentModel);
        }
        currentModel = {
          name: line.split('"')[1] || line.split("'")[1] || line.split(':')[1].trim(),
          tasks: []
        };
      } else if (line.startsWith('- service:') && currentModel) {
        const service = line.split('"')[1] || line.split("'")[1] || line.split(':')[1].trim();
        const numCorrect = parseInt(lines[i + 1].split(':')[1].trim());
        const numTotal = parseInt(lines[i + 2].split(':')[1].trim());
        const timeElapsed = parseFloat(lines[i + 3].split(':')[1].trim());
        
        currentModel.tasks.push({
          service: service,
          num_correct: numCorrect,
          num_total: numTotal,
          time_elapsed: timeElapsed
        });
        
        i += 3; // Skip the next 3 lines since we've processed them
      }
    }
    
    if (currentModel) {
      models.push(currentModel);
    }
    
    return { models: models };
  } catch (error) {
    console.error('Error loading performance data:', error);
    // Fallback to default data if YAML loading fails
    return {
      "models": [
        {
          "name": "claude-4-sonnect",
          "tasks": [
            {"service": "notion", "num_correct": 3, "num_total": 28, "time_elapsed": 264.1},
            {"service": "github", "num_correct": 2, "num_total": 14, "time_elapsed": 280},
            {"service": "filesystem", "num_correct": 7, "num_total": 21, "time_elapsed": 150}
          ]
        },
        {
          "name": "gpt-4.1",
          "tasks": [
            {"service": "notion", "num_correct": 3, "num_total": 28, "time_elapsed": 85.4},
            {"service": "github", "num_correct": 2, "num_total": 14, "time_elapsed": 60},
            {"service": "filesystem", "num_correct": 3, "num_total": 21, "time_elapsed": 40}
          ]
        }
      ]
    };
  }
}

function calculateModelStats(model) {
  let totalCorrect = 0;
  let totalTasks = 0;
  let totalTime = 0;
  
  model.tasks.forEach(task => {
    totalCorrect += task.num_correct;
    totalTasks += task.num_total;
    totalTime += task.time_elapsed;
  });
  
  return {
    name: model.name,
    avgAccuracy: totalTasks > 0 ? (totalCorrect / totalTasks * 100).toFixed(1) : 0,
    avgTime: (totalTime / model.tasks.length).toFixed(1)
  };
}

async function createBarChart() {
  const chartContainer = document.querySelector('[data-chart="chart-«Rshtejb»"] .recharts-responsive-container');
  if (!chartContainer) return;
  
  // Load data from YAML file
  const performanceData = await loadPerformanceData();
  const stats = performanceData.models.map(calculateModelStats);
  
  // Create chart HTML with side-by-side charts
  const chartHTML = `
    <div class="performance-chart">
      <div class="chart-header">
        <h3 class="text-lg font-semibold mb-4">Model Performance Overview</h3>
      </div>
      
      <div class="charts-container">
        <!-- Task Completion Chart -->
        <div class="chart-section">
          <h4 class="chart-title">Avg MCP Service Success-rate (%)</h4>
          <div class="chart-container">
            <div class="chart-row header">
              <div class="chart-cell model-name">Model</div>
              <div class="chart-cell">Success Rate</div>
            </div>
            
            ${stats.map(stat => {
              const model = performanceData.models.find(m => m.name === stat.name);
              const totalCorrect = model.tasks.reduce((sum, task) => sum + task.num_correct, 0);
              const totalTasks = model.tasks.reduce((sum, task) => sum + task.num_total, 0);
              return `
                <div class="chart-row">
                  <div class="chart-cell model-name">${stat.name}</div>
                  <div class="chart-cell">
                    <div class="accuracy-bar" 
                         data-tooltip="${totalCorrect}/${totalTasks} tasks completed"
                         onmouseover="showTooltip(this, '${totalCorrect}/${totalTasks} tasks completed')"
                         onmouseout="hideTooltip()">
                      <div class="accuracy-fill" style="width: ${Math.min(stat.avgAccuracy, 100)}%"></div>
                      <span class="accuracy-text">${stat.avgAccuracy}%</span>
                    </div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
        
        <!-- Time Chart -->
        <div class="chart-section">
          <h4 class="chart-title">Average Time Elapsed (seconds)</h4>
          <div class="chart-container">
            <div class="chart-row header">
              <div class="chart-cell model-name">Model</div>
              <div class="chart-cell">Time (s)</div>
            </div>
            
            ${stats.map(stat => {
              const model = performanceData.models.find(m => m.name === stat.name);
              const avgTimePerService = model.tasks.map(task => `${task.service}: ${task.time_elapsed}s`).join(', ');
              return `
                <div class="chart-row">
                  <div class="chart-cell model-name">${stat.name}</div>
                  <div class="chart-cell">
                    <div class="time-bar" 
                         data-tooltip="${avgTimePerService}"
                         onmouseover="showTooltip(this, '${avgTimePerService}')"
                         onmouseout="hideTooltip()">
                      <div class="time-fill" style="width: ${(stat.avgTime / Math.max(...stats.map(s => parseFloat(s.avgTime))) * 100)}%"></div>
                      <span class="time-text">${stat.avgTime}s</span>
                    </div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>
      
      <!-- Tooltip -->
      <div id="tooltip" class="tooltip"></div>
    </div>
  `;
  
  chartContainer.innerHTML = chartHTML;
}

// Tooltip functions
function showTooltip(element, text) {
  const tooltip = document.getElementById('tooltip');
  tooltip.textContent = text;
  tooltip.style.display = 'block';
  
  const rect = element.getBoundingClientRect();
  const tooltipRect = tooltip.getBoundingClientRect();
  
  // Position tooltip above the bar
  tooltip.style.left = (rect.left + rect.width / 2 - tooltipRect.width / 2) + 'px';
  tooltip.style.top = (rect.top - tooltipRect.height - 10) + 'px';
}

function hideTooltip() {
  const tooltip = document.getElementById('tooltip');
  tooltip.style.display = 'none';
}

// Add CSS styles
function addChartStyles() {
  const style = document.createElement('style');
  style.textContent = `
    .performance-chart {
      padding: 20px;
      font-family: monospace;
      position: relative;
    }
    
    .chart-header {
      text-align: center;
      margin-bottom: 20px;
    }
    
    .charts-container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 30px;
      max-width: 100%;
    }
    
    .chart-section {
      display: flex;
      flex-direction: column;
    }
    
    .chart-title {
      text-align: center;
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 15px;
      color: #374151;
    }
    
    .chart-container {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
      flex: 1;
    }
    
    .chart-row {
      display: flex;
      border-bottom: 1px solid #f1f5f9;
    }
    
    .chart-row:last-child {
      border-bottom: none;
    }
    
    .chart-row.header {
      background-color: #f8fafc;
      font-weight: 600;
    }
    
    .chart-cell {
      flex: 1;
      padding: 12px 16px;
      display: flex;
      align-items: center;
    }
    
    .model-name {
      font-weight: 500;
      color: #1e293b;
    }
    
    .accuracy-bar, .time-bar {
      position: relative;
      width: 100%;
      height: 16px;
      background-color: #e2e8f0;
      border-radius: 0px;
      overflow: hidden;
      cursor: pointer;
    }
    
    .accuracy-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #1d4ed8);
      transition: width 0.3s ease;
    }
    
    .time-fill {
      height: 100%;
      background: linear-gradient(90deg, #10b981, #059669);
      transition: width 0.3s ease;
    }
    
    .accuracy-text, .time-text {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 11px;
      font-weight: 600;
      color: #1e293b;
      text-shadow: 0 0 2px rgba(255,255,255,0.8);
    }
    
    .tooltip {
      position: fixed;
      display: none;
      background-color: #1f2937;
      color: white;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-family: monospace;
      z-index: 1000;
      pointer-events: none;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
      max-width: 200px;
      text-align: center;
    }
    
    .tooltip::after {
      content: '';
      position: absolute;
      top: 100%;
      left: 50%;
      margin-left: -5px;
      border-width: 5px;
      border-style: solid;
      border-color: #1f2937 transparent transparent transparent;
    }
    
    @media (max-width: 768px) {
      .charts-container {
        grid-template-columns: 1fr;
        gap: 20px;
      }
      
      .chart-cell {
        padding: 8px 12px;
        font-size: 14px;
      }
      
      .accuracy-text, .time-text {
        font-size: 10px;
      }
      
      .accuracy-bar, .time-bar {
        height: 14px;
      }
    }
  `;
  document.head.appendChild(style);
}

// Initialize chart when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  addChartStyles();
  createBarChart();
});

// Also try to create chart if DOM is already loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', createBarChart);
} else {
  createBarChart();
}
