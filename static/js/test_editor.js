document.addEventListener('DOMContentLoaded', function() {
    let testData = window.testData || {};
    let questionEditors = [];
    let optionEditors = [];
    
    // Initialize Select2
    $('#subject-select').select2();
    
    // Handle subject change
    $('#subject-select').on('change', function() {
        const subject = $(this).val();
        $('#subject-input').val(subject);
    });
    
    // Initialize subject input
    $('#subject-input').val($('#subject-select').val());
    
    function createQuillEditor(container, placeholder) {
        return new Quill(container, {
            theme: 'snow',
            placeholder: placeholder,
            modules: {
                toolbar: [
                    ['bold', 'italic', 'underline'],
                    [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                    ['link', 'image'],
                    ['clean']
                ]
            }
        });
    }
    
    function createQuestion(index, data = null) {
        const template = document.getElementById('question-template');
        const container = document.getElementById('questions-container');
        const questionHtml = template.innerHTML
            .replace(/{index}/g, index)
            .replace(/{number}/g, index + 1);
            
        const questionDiv = document.createElement('div');
        questionDiv.innerHTML = questionHtml;
        container.appendChild(questionDiv);
        
        // Initialize question editor
        const editorContainer = questionDiv.querySelector('.question-editor');
        const editor = createQuillEditor(editorContainer, 'Enter your question here...');
        questionEditors[index] = editor;
        
        if (data) {
            editor.root.innerHTML = data.content;
            const typeInput = questionDiv.querySelector(`input[name="question-type-${index}"][value="${data.type}"]`);
            if (typeInput) typeInput.checked = true;
            
            if (data.options) {
                data.options.forEach((option, optIndex) => {
                    createOption(index, optIndex, option, data.correctIndex === optIndex);
                });
            }
        }
        
        // Event listeners
        questionDiv.querySelector('.delete-question').addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this question?')) {
                questionDiv.remove();
                updateQuestionNumbers();
            }
        });
        
        questionDiv.querySelector('.add-option-btn').addEventListener('click', () => {
            const optionsCount = questionDiv.querySelectorAll('.option-item').length;
            createOption(index, optionsCount);
        });
        
        // Add initial options if none exist
        if (!data || !data.options || data.options.length === 0) {
            createOption(index, 0);
            createOption(index, 1);
        }
    }
    
    function createOption(questionIndex, optionIndex, content = '', isCorrect = false) {
        const template = document.getElementById('option-template');
        const questionDiv = document.querySelector(`[data-index="${questionIndex}"]`);
        const optionsContainer = questionDiv.querySelector('.options-list');
        
        const optionHtml = template.innerHTML
            .replace(/{questionIndex}/g, questionIndex)
            .replace(/{optionIndex}/g, optionIndex);
            
        const optionDiv = document.createElement('div');
        optionDiv.innerHTML = optionHtml;
        optionsContainer.appendChild(optionDiv);
        
        // Initialize option editor
        const editorContainer = optionDiv.querySelector('.option-editor');
        const editor = createQuillEditor(editorContainer, 'Enter option text...');
        if (!optionEditors[questionIndex]) optionEditors[questionIndex] = [];
        optionEditors[questionIndex][optionIndex] = editor;
        
        if (content) {
            editor.root.innerHTML = content;
        }
        
        const radioInput = optionDiv.querySelector('input[type="radio"]');
        radioInput.checked = isCorrect;
        
        // Delete option handler
        optionDiv.querySelector('.delete-option').addEventListener('click', () => {
            if (optionsContainer.querySelectorAll('.option-item').length > 1) {
                optionDiv.remove();
            } else {
                alert('A question must have at least one option');
            }
        });
    }
    
    function updateQuestionNumbers() {
        document.querySelectorAll('.question-item').forEach((item, index) => {
            item.querySelector('h3').textContent = `Question ${index + 1}`;
        });
    }
    
    function getTestData() {
        const questions = [];
        document.querySelectorAll('.question-item').forEach((item, index) => {
            const questionType = item.querySelector(`input[name="question-type-${index}"]:checked`).value;
            const content = questionEditors[index].root.innerHTML;
            const question = { type: questionType, content: content };

            if (questionType === 'multiple_choice') {
                question.options = [];
                let correctIndex = -1;

                item.querySelectorAll('.option-item').forEach((option, optIndex) => {
                    const optionContent = optionEditors[index][optIndex].root.innerHTML;
                    question.options.push(optionContent);

                    if (option.querySelector('input[type="radio"]').checked) {
                        correctIndex = optIndex;
                    }
                });

                question.correctIndex = correctIndex;
            }

            questions.push(question);
        });

        return {
            title: document.getElementById('test-title').value,
            questions: questions,
            created_at: testData.created_at || new Date().toISOString()
        };
    }
    
    // Initialize existing questions
    if (testData.questions) {
        testData.questions.forEach((question, index) => {
            createQuestion(index, question);
        });
    }
    
    // Add question button handler
    document.getElementById('add-question').addEventListener('click', () => {
        const questionCount = document.querySelectorAll('.question-item').length;
        createQuestion(questionCount);
    });
    
    // Save changes handler
    document.getElementById('save-changes').addEventListener('click', () => {
        const title = document.getElementById('test-title').value;
        if (!title) {
            alert('Please enter a test title');
            return;
        }
        
        const data = getTestData();
        if (data.questions.length === 0) {
            alert('Please add at least one question');
            return;
        }
        
        // Populate hidden form inputs
        document.getElementById('test_content').value = JSON.stringify(data);
        document.getElementById('test-name-input').value = title;
        
        // Submit the form
        document.getElementById('test-form').submit();
    });
}); 