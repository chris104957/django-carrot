Vue.component('task-detail', {
    delimiters: ['[[', ']]'],
    props: ['task', 'logLevel'],
    filters: {
        formatDate: function(rawDate) {
            // filter for converting a raw string to something more human-readable
            return moment(String(rawDate)).format('DD/MM/YYYY hh:mm')
        },
        sentence: function(raw) {
            // convert "STRING" to "String"
            var firstLetter = raw.substr(0, 1);
            var rest = raw.substr(1);
            return firstLetter + rest.toLowerCase();
        }
    },
    methods: {
        splitTraceback: function(rawTraceback) {
            // splits a task's traceback at the line breaks
            return rawTraceback.split('\n');
        },
        getLevel: function() {
            var levels = {
                DEBUG: 1,
                INFO: 2,
                WARNING: 3,
                ERROR: 4,
                CRITICAL: 5
            };
            var elem = document.getElementById('selector');
            var levelNumber;
            if (elem) {
                return levels[elem.value];
            } else {
                return 2;
            };
        },
        renderLog: function(rawLog) {
            // converts the lines of the rawLog object to a list of dictionaries
            var levels = {
                DEBUG: 1,
                INFO: 2,
                WARNING: 3,
                ERROR: 4,
                CRITICAL: 5
            };

            var rawLines = rawLog.split('\n');
            var output = [];

            for (i = 0; i < rawLines.length; i ++) {
                if (rawLines[i]) {
                    var splitLine = rawLines[i].split('::')
                    var preColon = splitLine[0].split(' ')
                    var message = splitLine[1]

                    var rowData = {
                        consumer: preColon[0],
                        date: preColon[1],
                        time: preColon[2],
                        level: levels[preColon[3]],
                        message: message,
                    };
                    output.push(rowData);
                }
            };
            console.log(output);
            return output;
        },
        getIndent: function(line) {
            // calculates the indent_level class to apply to the LI elements in the traceback, eg class="indent_level_2"
            var level = (line.length - line.trim().length) / 2;
            return 'indent_level_' + level;
        }
    },
    template: '{{ task_detail_template }}',
})


var app = new Vue({
    el: '#app',
    delimiters: ['[[', ']]'],

    data: {
        highlightMode: false,
        selectedObjectId: null,
        selectedObject: null,
        logLevel: 3,
        logLevels: {
            DEBUG: 1,
            INFO: 2,
            WARNING: 3,
            ERROR: 4,
            CRITICAL: 5
        };

        publishedObjects: [],
        publishedPage: 1,
        publishedPageCount: 0,
        publishedPreviousPage: null,
        publishedNextPage: null,

        failedObjects: [],
        failedPage: 1,
        failedPageCount: 0,
        failedPreviousPage: null,
        failedNextPage: null,

        completedObjects: [],
        completedPage: 1,
        completedPageCount: 0,
        completedPreviousPage: null,
        completedNextPage: null,

        scheduledObjects: [],
        scheduledPage: 1,
        scheduledPageCount: 0,
        scheduledPreviousPage: null,
        scheduledNextPage: null,
    },
    created: function () {
        this.getPublishedMessageLogs()
        this.getFailedMessageLogs()
        this.getCompletedMessageLogs()
        this.getScheduledTasks()
    },
    filters: {
        formatDate: function(rawDate) {
            // filter for converting a raw string to something more human-readable
            return moment(String(rawDate)).format('DD/MM/YYYY hh:mm')
        },
    },
    methods: {
        // methods for determining whether the next/previous pagingation buttons should be disabled
        publishedPreviousDisabled: function () {
            if (this.publishedPage <= 1) {
                return true
            }
            if (!this.publishedPreviousPage) {
                return true
            };
            return false;
        },
        publishedNextDisabled: function () {
            if (!this.publishedNextPage) {
                return true
            }
        },
        failedPreviousDisabled: function () {
            if (this.failedPage <= 1) {
                return true
            }
            if (!this.failedPreviousPage) {
                return true
            };
            return false;
        },
        failedNextDisabled: function () {
            if (!this.failedNextPage) {
                return true
            }
        },
        completedPreviousDisabled: function () {
            if (this.completedPage <= 1) {
                return true
            }
            if (!this.completedPage) {
                return true
            };
            return false;
        },
        completedNextDisabled: function () {
            if (!this.completedNextPage) {
                return true
            }
        },
        scheduledPreviousDisabled: function () {
            if (this.scheduledPage <= 1) {
                return true
            }
            if (!this.scheduledPage) {
                return true
            };
            return false;
        },
        scheduledNextDisabled: function () {
            if (!this.scheduledNextPage) {
                return true
            }
        },
        // methods for bumping/reducing the page numbers
        bumpPublishedPage: function () {
            this.publishedPage = parseInt(this.publishedPage) + 1;
        },
        prevPublishedPage: function () {
            this.publishedPage = parseInt(this.publishedPage) - 1;
        },
        bumpFailedPage: function () {
            this.failedPage = parseInt(this.failedPage) + 1;
        },
        prevFailedPage: function () {
            this.failedPage = parseInt(this.failedPage) - 1;
        },
        bumpCompletedPage: function () {
            this.completedPage = parseInt(this.completedPage) + 1;
        },
        prevCompletedPage: function () {
            this.completedPage = parseInt(this.completedPage) - 1;
        },
        bumpScheduledPage: function () {
            this.scheduledPage = parseInt(this.scheduledPage) + 1;
        },
        prevScheduledPage: function () {
            this.scheduledPage = parseInt(this.scheduledPage) - 1;
        },
        // methods for calling the REST API
        getPublishedMessageLogs: function () {
            var self = this;
            return axios.get('/carrot/api/message-logs/published/?page=' + self.publishedPage)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/10);
                if (pages != count/10) {
                    pages = pages + 1;
                };
                self.publishedPreviousPage = response.data.previous;
                self.publishedPageCount = pages;
                self.publishedNextPage = response.data.next;
                self.publishedObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
                this.fetchError = error
            })
        },
        getFailedMessageLogs: function () {
            var self = this;
            return axios.get('/carrot/api/message-logs/failed/?page=' + self.failedPage)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/10);
                if (pages != count/10) {
                    pages = pages + 1;
                };

                self.failedPreviousPage = response.data.previous;
                self.failedPageCount = pages;
                self.failedNextPage = response.data.next;
                self.failedObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
                this.fetchError = error
            })
        },
        getCompletedMessageLogs: function () {
            var self = this;
            return axios.get('/carrot/api/message-logs/completed/?page=' + self.completedPage)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/10);
                if (pages != count/10) {
                    pages = pages + 1;
                };

                self.completedPreviousPage = response.data.previous;
                self.completedPageCount = pages;
                self.completedNextPage = response.data.next;
                self.completedObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
                this.fetchError = error
            })
        },
        getScheduledTasks: function () {
            var self = this;
            return axios.get('/carrot/api/scheduled-tasks/?page=' + self.scheduledPage)
            .then(function (response) {
                var count = response.data.count;
                var pages = parseInt(count/10);
                if (pages != count/10) {
                    pages = pages + 1;
                };

                self.scheduledPreviousPage = response.data.previous;
                self.scheduledPageCount = pages;
                self.scheduledNextPage = response.data.next;
                self.scheduledObjects = response.data.results
            })
            .catch(function (error) {
                console.log(error);
                this.fetchError = error
            })
        },
        highlight: function(event) {
            var self = this;
            var elementId = event.target.parentElement.id;
            var taskId = elementId.split('_')[1];
            var overlay = document.getElementById('overlay');
            self.highlightMode = true;
            self.selectedObjectId = taskId;
        },
        hideOverlay: function() {
            this.highlightMode = false;
            this.selectedObjectId = null;
            this.selectedObject = null;
        },
        getTask: function(taskId) {
            // returns the data for a single task object by calling the REST API
            var self = this;
            return axios.get('/carrot/api/message-logs/' + self.selectedObjectId)
            .then(function (response) {
                self.selectedObject = response.data;
            })
            .catch(function (error) {
                console.log(error);
                this.fetchError = error
            })
        }
    }
})

// watchers that look for changes to the page numbers
app.$watch('publishedPage', function (newVal, oldVal) {
    app.getPublishedMessageLogs()
})

app.$watch('failedPage', function (newVal, oldVal) {
    app.getFailedMessageLogs()
})

app.$watch('completedPage', function (newVal, oldVal) {
    app.getCompletedMessageLogs()
})

app.$watch('scheduledPage', function (newVal, oldVal) {
    app.getCompletedMessageLogs()
})

// watcher that calls app.getTask() whenever there is a change to the selected object pk, and that pk is not null
app.$watch('selectedObjectId', function (newVal, oldVal) {
    if (newVal) {
        app.getTask();
    }
})


