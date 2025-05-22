document.addEventListener('DOMContentLoaded', function() {
    let testData = window.testData || {};
    let questionEditors = [];
    
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
        let questionHtml = template.innerHTML
            .replace(/\{index\}/g, index)
            .replace(/\{number\}/g, index + 1);
        const questionDiv = document.createElement('div');
        questionDiv.innerHTML = questionHtml;
        container.appendChild(questionDiv);
        
        // Initialize question editor
        const editorContainer = questionDiv.querySelector('.question-editor');
        const editor = createQuillEditor(editorContainer, 'Enter your question here...');
        questionEditors[index] = editor;
        
        // Set up question type change handler
        const typeSelect = questionDiv.querySelector('.question-type');
        const optionsContainer = questionDiv.querySelector('.options-container');
        // Golesc complet optionsContainer și inserez doar butonul Add Option
        optionsContainer.innerHTML = '';
        const addOptionBtn = document.createElement('button');
        addOptionBtn.className = 'btn btn-info add-option-btn';
        addOptionBtn.innerHTML = '<i class="fas fa-plus"></i> Add Option';
        optionsContainer.appendChild(addOptionBtn);
        
        function updateOptionsVisibility() {
            let type = '';
            // Support both radio and select for question type
            if (typeSelect.tagName === 'SELECT') {
                type = typeSelect.value;
            } else {
                const checkedRadio = questionDiv.querySelector('.question-type input[type="radio"]:checked');
                type = checkedRadio ? checkedRadio.value : '';
            }
            if (type === 'multiple_choice') {
                optionsContainer.style.display = 'block';
                // Adaug opțiuni implicite doar dacă nu există deja opțiuni
                if (optionsContainer.querySelectorAll('.option-item').length === 0) {
                    if (!data || !data.options || !Array.isArray(data.options) || data.options.length === 0) {
                        createOption(questionDiv, '');
                        createOption(questionDiv, '');
                        createOption(questionDiv, '');
                    }
                }
            } else {
                optionsContainer.style.display = 'none';
            }
        }
        typeSelect.addEventListener('change', updateOptionsVisibility);
        
        // Event listeners
        questionDiv.querySelector('.remove-question-btn').addEventListener('click', () => {
            if (confirm('Are you sure you want to delete this question?')) {
                questionDiv.remove();
            }
        });
        
        // Butonul Add Option
        addOptionBtn.addEventListener('click', (e) => {
            e.preventDefault();
            createOption(questionDiv, '');
        });
        
        // Inițializează cu date dacă există
        if (data) {
            editor.root.innerHTML = data.content;
            if (typeSelect) {
                // For radio buttons, set the correct one as checked
                const radios = questionDiv.querySelectorAll('.question-type input[type="radio"]');
                if (radios.length) {
                    radios.forEach(radio => {
                        radio.checked = (radio.value === data.type);
                    });
                } else {
                    typeSelect.value = data.type;
                }
            }
            updateOptionsVisibility();
            if (data.options && Array.isArray(data.options)) {
                optionsContainer.innerHTML = '';
                optionsContainer.appendChild(addOptionBtn);
                data.options.forEach((option, optIndex) => {
                    createOption(questionDiv, option, data.correctIndex === optIndex);
                });
            }
        } else {
            updateOptionsVisibility();
        }
    }
    
    function createOption(questionDiv, content = '', isCorrect = false) {
        const optionsContainer = questionDiv.querySelector('.options-container');
        const optionTemplate = `
            <div class="option-item mb-2">
                <input type="radio" name="correct-${Date.now()}" class="correct-option">
                <div class="option-editor"></div>
                <button class="remove-option-btn btn btn-danger">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        // Creez un element temporar pentru a extrage .option-item
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = optionTemplate;
        const optionItem = tempDiv.firstElementChild;
        // Adaug opțiunea înainte de butonul Add Option
        optionsContainer.insertBefore(optionItem, optionsContainer.querySelector('.add-option-btn'));
        // Initializez Quill pe .option-editor
        const editorContainer = optionItem.querySelector('.option-editor');
        const editor = createQuillEditor(editorContainer, 'Enter option text...');
        optionItem.quillEditor = editor;
        if (content) {
            editor.root.innerHTML = content;
        }
        const radioInput = optionItem.querySelector('input[type="radio"]');
        radioInput.checked = isCorrect;
        // Delete option handler
        optionItem.querySelector('.remove-option-btn').addEventListener('click', () => {
            if (optionsContainer.querySelectorAll('.option-item').length > 1) {
                optionItem.remove();
            } else {
                alert('A question must have at least one option');
            }
        });
    }
    
    function getTestData() {
        const questions = [];
        document.querySelectorAll('.question-item').forEach((item, index) => {
            const questionType = item.querySelector('.question-type').value;
            const content = questionEditors[index]?.root?.innerHTML || '';
            const question = { type: questionType, content: content };

            if (questionType === 'multiple_choice') {
                question.options = [];
                let correctIndex = -1;

                item.querySelectorAll('.option-item').forEach((option, optIndex) => {
                    // Extrag conținutul direct din Quill-ul atașat DOM-ului
                    const optionEditor = option.quillEditor;
                    const optionContent = optionEditor ? optionEditor.root.innerHTML : '';
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
    document.getElementById('test-form').addEventListener('submit', function(e) {
        e.preventDefault();
        const data = getTestData();
        const subject = document.getElementById('subject-select').value;
        const test_name = document.getElementById('test-title').value;
        const test_content = JSON.stringify(data);

        // Validate that we have questions
        if (data.questions.length === 0) {
            alert('Please add at least one question to the test');
            return;
        }

        // Validate each question
        for (let i = 0; i < data.questions.length; i++) {
            const question = data.questions[i];
            if (!question.content || question.content.trim() === '') {
                alert(`Question ${i + 1} has no content`);
                return;
            }
            if (question.type === 'multiple_choice') {
                if (!question.options || question.options.length === 0) {
                    alert(`Question ${i + 1} has no options`);
                    return;
                }
                if (question.correctIndex === -1) {
                    alert(`Question ${i + 1} has no correct answer selected`);
                    return;
                }
            }
        }

        const formData = new FormData();
        formData.append('subject', subject);
        formData.append('test_name', test_name);
        formData.append('test_content', test_content);

        fetch(window.location.pathname, {
            method: 'POST',
            body: formData
        })
        .then(async response => {
            let respText = await response.text();
            if (response.ok && respText.toLowerCase().includes('test') && !respText.toLowerCase().includes('error')) {
                alert('Test saved successfully!');
                window.location.reload();
            } else {
                alert('Error saving test: ' + respText);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error saving test: ' + error.message);
        });
    });

    // Funcție globală pentru ștergerea testelor
    window.deleteTest = function(subject, title) {
        if (!confirm('Are you sure you want to delete this test?')) return;
        fetch(`/studio/delete-test/${subject}/${title}`, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(res => {
            if (res.redirected) {
                window.location.href = res.url;
            } else {
                window.location.reload();
            }
        })
        .catch(err => {
            alert('Error deleting test.');
        });
    }
}); 