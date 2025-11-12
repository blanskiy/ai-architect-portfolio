# ============================================================================
# PHASE 2: Enhance Existing Projects
# ============================================================================
# This script moves existing projects to new structure and adds enhancement templates
# Run this AFTER Phase 1
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PHASE 2: Enhancing Existing Projects" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verify we're in the right directory
if (-not (Test-Path ".git")) {
    Write-Host "ERROR: Not in a git repository root!" -ForegroundColor Red
    exit 1
}

Write-Host "Current directory: $(Get-Location)" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Project Mapping: Old to New Location
# ============================================================================

$projectMappings = @{
    # Foundations
    "projects/01-ml-basics" = "projects/01-foundations/ml-basics"
    "projects/02-deep-learning-cnn" = "projects/01-foundations/deep-learning-cnn"
    
    # LLM Mastery
    "projects/03-nlp-transformers" = "projects/02-llm-mastery/transformers-deep-dive"
    "projects/04-huggingface-finetuning" = "projects/02-llm-mastery/llm-finetuning"
    "projects/05-llm-embeddings" = "projects/02-llm-mastery/llm-embeddings"
    "projects/06-langchain-rag" = "projects/02-llm-mastery/production-rag"
    
    # MLOps Production
    "projects/07-azure-ml-mlops-demo" = "projects/03-mlops-production/mlops-cicd-pipeline"
    "projects/08-capstone-rag-enterprise-assistant" = "projects/03-mlops-production/rag-enterprise-assistant"
    "projects/09-capstone-mlops-churn-prediction" = "projects/03-mlops-production/churn-prediction-capstone"
    
    # Databricks Enterprise
    "projects/10-databricks-ai-overview" = "projects/04-databricks-enterprise/databricks-overview"
}

Write-Host "Step 1: Moving existing projects to new structure..." -ForegroundColor Yellow
Write-Host ""

foreach ($oldPath in $projectMappings.Keys) {
    $newPath = $projectMappings[$oldPath]
    
    if (Test-Path $oldPath) {
        $parentDir = Split-Path $newPath -Parent
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }
        
        Write-Host "  Moving: $oldPath" -ForegroundColor Yellow
        Write-Host "      to: $newPath" -ForegroundColor Green
        
        try {
            git mv $oldPath $newPath 2>$null
            Write-Host "  Moved using git" -ForegroundColor Green
        } catch {
            Move-Item -Path $oldPath -Destination $newPath -Force
            Write-Host "  Moved using filesystem" -ForegroundColor Green
        }
    } else {
        Write-Host "  Not found: $oldPath (skipping)" -ForegroundColor Gray
    }
}

Write-Host ""

# ============================================================================
# Add ENHANCEMENT.md to each existing project
# ============================================================================

Write-Host "Step 2: Adding ENHANCEMENT.md checklist to each project..." -ForegroundColor Yellow
Write-Host ""

function Get-EnhancementTemplate {
    param($projectName, $priority, $monthWeek)
    
    return @"
# Enhancement Checklist: $projectName

**Priority**: $priority  
**Target Completion**: $monthWeek  
**Status**: In Progress

## Current State Assessment
- [x] Basic implementation exists
- [x] Jupyter notebook OR Python scripts
- [ ] Production-grade code structure
- [ ] Comprehensive documentation
- [ ] Architecture diagram
- [ ] Quantitative metrics documented
- [ ] Demo video recorded

## Critical Gaps (Must Fix for Portfolio)

### 1. Architecture Diagram
- [ ] Create high-level architecture diagram
- [ ] Show data flow with arrows
- [ ] Label all components
- [ ] Export as PNG to /docs folder
- [ ] Add diagram to README

### 2. Quantitative Metrics
- [ ] Add Results section to README
- [ ] Document performance metrics
- [ ] Add cost analysis
- [ ] Create comparison table
- [ ] Include charts if applicable

### 3. Documentation Enhancement
- [ ] Clear problem statement
- [ ] Tech stack table
- [ ] Setup instructions
- [ ] Trade-offs and Learnings section
- [ ] Link to related projects
- [ ] Add Interview Story section

### 4. Code Quality
- [ ] Refactor notebooks into modular .py files
- [ ] Add error handling and logging
- [ ] Add docstrings
- [ ] Add type hints
- [ ] Create requirements.txt
- [ ] Add .gitignore if missing

### 5. Demo and Presentation
- [ ] Record demo video (5-7 minutes)
- [ ] Upload to YouTube or Loom
- [ ] Add link to README
- [ ] Write blog post about learnings

## Enhancement Tasks by Priority

### HIGH PRIORITY (Do This Week)
1. [ ] Add architecture diagram
2. [ ] Document metrics in README
3. [ ] Add cost analysis
4. [ ] Write Trade-offs section

### MEDIUM PRIORITY (Do Next Week)
5. [ ] Refactor code structure
6. [ ] Add error handling
7. [ ] Create setup instructions
8. [ ] Add docstrings

### LOW PRIORITY (Nice to Have)
9. [ ] Record demo video
10. [ ] Write blog post
11. [ ] Add unit tests

## Microsoft Interview Preparation

### STAR Story for This Project
**Situation**: [Context - what was the business problem]  
**Task**: [Your responsibility]  
**Action**: [What YOU did]  
**Result**: [Outcomes with metrics]

**Technical Follow-ups to Prepare**:
- [ ] How would you scale this to 10x traffic?
- [ ] What would you do differently?
- [ ] What trade-offs did you make and why?

---

Started: $(Get-Date -Format 'yyyy-MM-dd')  
Target Completion: $monthWeek
"@
}

# Apply enhancement templates to critical projects
$projectEnhancements = @(
    @{Path="projects/02-llm-mastery/production-rag"; Name="Production RAG System"; Priority="CRITICAL"; MonthWeek="Month 2, Week 2"},
    @{Path="projects/02-llm-mastery/llm-finetuning"; Name="LLM Fine-tuning"; Priority="CRITICAL"; MonthWeek="Month 2, Week 3"},
    @{Path="projects/03-mlops-production/mlops-cicd-pipeline"; Name="MLOps CI/CD Pipeline"; Priority="CRITICAL"; MonthWeek="Month 3, Week 1"},
    @{Path="projects/03-mlops-production/churn-prediction-capstone"; Name="Churn Prediction Capstone"; Priority="CRITICAL"; MonthWeek="Month 3, Week 4"},
    @{Path="projects/01-foundations/deep-learning-cnn"; Name="Deep Learning CNN"; Priority="IMPORTANT"; MonthWeek="Month 1, Week 1-2"},
    @{Path="projects/02-llm-mastery/transformers-deep-dive"; Name="Transformers Deep Dive"; Priority="SUPPORTING"; MonthWeek="Month 2, Week 1"}
)

foreach ($project in $projectEnhancements) {
    if (Test-Path $project.Path) {
        $enhancementPath = "$($project.Path)/ENHANCEMENT.md"
        $template = Get-EnhancementTemplate -projectName $project.Name -priority $project.Priority -monthWeek $project.MonthWeek
        Set-Content -Path $enhancementPath -Value $template
        Write-Host "  Created: $enhancementPath" -ForegroundColor Green
    } else {
        Write-Host "  Project not found: $($project.Path)" -ForegroundColor Gray
    }
}

Write-Host ""

# ============================================================================
# Add metrics template
# ============================================================================

Write-Host "Step 3: Adding METRICS_TEMPLATE.md..." -ForegroundColor Yellow
Write-Host ""

$metricsTemplate = @"
# Project Metrics Template

Copy this into your README.md under Results section.

## Performance Metrics

### Model Performance
| Metric | Value | Target | Status | Notes |
|--------|-------|--------|--------|-------|
| Accuracy | X% | Y% | Status | |
| Precision | X | Y | Status | |
| Recall | X | Y | Status | |

### System Performance
| Metric | Value | Target | Status | Notes |
|--------|-------|--------|--------|-------|
| Throughput (RPS) | X | Y | Status | Requests per second |
| p50 Latency | Xms | Yms | Status | Median latency |
| p99 Latency | Xms | Yms | Status | 99th percentile |

### Cost Analysis
| Resource | Monthly Cost | Usage | Optimization |
|----------|--------------|-------|--------------|
| Azure ML Compute | X | Y hours | |
| Azure OpenAI | X | Y tokens | |
| TOTAL | X | | |

## Tips for Documenting Metrics

1. Be Specific: Do not say fast - say 45ms p99 latency
2. Show Trade-offs: Chose X over Y because...
3. Include Context: On Azure NC6s_v3 with 1 GPU...
4. Document Failures: Initial approach failed because...
5. Cost Consciousness: Always document Azure spend
"@

Set-Content -Path "architecture-diagrams/METRICS_TEMPLATE.md" -Value $metricsTemplate
Write-Host "  Created: METRICS_TEMPLATE.md" -ForegroundColor Green

Write-Host ""

# ============================================================================
# Create diagram checklist
# ============================================================================

Write-Host "Step 4: Creating architecture diagram checklist..." -ForegroundColor Yellow
Write-Host ""

$diagramChecklist = @"
# Architecture Diagram Creation Checklist

## Priority Projects (Create These First)

### 1. High-Throughput Model Serving
**File**: high-throughput-serving-architecture.png  
**Components to Show**:
- [ ] Load Balancer
- [ ] API Gateway
- [ ] Model Serving Layer
- [ ] Caching Layer (Redis)
- [ ] Monitoring
- [ ] Autoscaler

**Status**: To Do  
**Deadline**: Month 1, Week 4

---

### 2. Production RAG System
**File**: production-rag-architecture.png  
**Components to Show**:
- [ ] User Query Input
- [ ] Query Router
- [ ] Embedding Model
- [ ] Vector Database
- [ ] Hybrid Search
- [ ] Reranking Layer
- [ ] LLM Generation
- [ ] Response Validation

**Status**: To Do  
**Deadline**: Month 2, Week 2

---

### 3. MLOps CI/CD Pipeline
**File**: mlops-cicd-pipeline.png  
**Components to Show**:
- [ ] GitHub Repository
- [ ] GitHub Actions
- [ ] Data Validation
- [ ] Model Training
- [ ] Model Registry
- [ ] Production Deployment
- [ ] Monitoring and Drift Detection

**Status**: To Do  
**Deadline**: Month 3, Week 1

---

## Design Guidelines

### Color Coding Standard
Blue: Data and Storage  
Green: Processing and Compute  
Orange: ML and AI Services  
Red: Monitoring and Alerts  
Purple: External Services  

### Must Include in Every Diagram
- [ ] Title at top
- [ ] Legend explaining icons
- [ ] Data flow arrows
- [ ] Labels on all components
- [ ] Technology names
- [ ] Key metrics annotations

### Export Settings
- Format: PNG
- Resolution: 300 DPI minimum
- Size: 1920x1080 or larger
- Background: White

---

## Quick Start with Draw.io

1. Go to https://app.diagrams.net/
2. Choose Device - save locally
3. Start with blank diagram
4. Add shapes from left sidebar
5. Color code using guidelines
6. Add labels with large font (14pt+)
7. Export: File - Export as - PNG

Track Progress: Update this checklist as you create diagrams
"@

Set-Content -Path "architecture-diagrams/DIAGRAM_CHECKLIST.md" -Value $diagramChecklist
Write-Host "  Created: DIAGRAM_CHECKLIST.md" -ForegroundColor Green

Write-Host ""

# ============================================================================
# Summary
# ============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PHASE 2 COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  Moved existing projects to new structure" -ForegroundColor Green
Write-Host "  Added ENHANCEMENT.md to critical projects" -ForegroundColor Green
Write-Host "  Created metrics tracking template" -ForegroundColor Green
Write-Host "  Created architecture diagram checklist" -ForegroundColor Green
Write-Host ""
Write-Host "Your Projects Now:" -ForegroundColor Yellow
Write-Host "  01-foundations/" -ForegroundColor White
Write-Host "    - ml-basics" -ForegroundColor Gray
Write-Host "    - deep-learning-cnn" -ForegroundColor Gray
Write-Host "    - high-throughput-serving (NEW - CRITICAL)" -ForegroundColor Green
Write-Host ""
Write-Host "  02-llm-mastery/" -ForegroundColor White
Write-Host "    - production-rag (CRITICAL)" -ForegroundColor Yellow
Write-Host "    - llm-finetuning (CRITICAL)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  03-mlops-production/" -ForegroundColor White
Write-Host "    - mlops-cicd-pipeline (CRITICAL)" -ForegroundColor Yellow
Write-Host "    - churn-prediction-capstone (CRITICAL)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Action Items:" -ForegroundColor Yellow
Write-Host "  1. Review ENHANCEMENT.md in each critical project" -ForegroundColor White
Write-Host "  2. Use METRICS_TEMPLATE.md to document results" -ForegroundColor White
Write-Host "  3. Use DIAGRAM_CHECKLIST.md to create diagrams" -ForegroundColor White
Write-Host "  4. Run Phase 3 script to create main README" -ForegroundColor White
Write-Host ""
Write-Host "Next: Run phase3_create_main_readme.ps1" -ForegroundColor Cyan
Write-Host ""
