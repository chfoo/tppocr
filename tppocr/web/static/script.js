function main() {
    console.info("Running!");

    var statusElement = document.getElementById("status_container");
    var debugImagesContainer = document.getElementById("debug_images_container");
    var rawTextsContainer = document.getElementById("raw_texts_container");
    var outputTextsContainer = document.getElementById("output_texts_container");
    var reconnectTimer = null;
    var backoffCounter = 0;

    function handleMessage(message) {
        var doc = JSON.parse(message.data);

        renderMessageDoc(doc);
    }

    function renderMessageDoc(doc) {
        switch (doc["type"]) {
        case "debug_image":
            var containerId = "debug_image_container_" + doc["section"];
            var containerElement = document.getElementById(containerId);
            var formattedDates = formatTimestamps(doc["timestamp"]);

            if (!containerElement) {
                containerElement = document.createElement("div");
                containerElement.id = containerId;
                containerElement.class = "debug_image-container";
                $(containerElement).html(
                    Mustache.render(
                        $('#debug_image_template').html(),
                        {"section_name": doc["section"]}
                    )
                );

                debugImagesContainer.appendChild(containerElement);
            }

            $(containerElement).find(".debug_image").prop(
                'src',
                "data:" + doc["format"] + "," + doc["image"]
            )
            $(containerElement).find(".debug_image-time")
                .attr("datetime", formattedDates["iso_date"])
                .text(formattedDates["date_string"])
                .timeago()
                .timeago("updateFromDOM");
            break;
        case "raw_text":
            var containerId = "raw_text_container_" + doc["section"];
            var containerElement = document.getElementById(containerId);
            var formattedDates = formatTimestamps(doc["timestamp"]);

            if (!containerElement) {
                containerElement = document.createElement("div");
                containerElement.id = containerId;
                containerElement.class = "raw_text-container";
                $(containerElement).html(
                    Mustache.render(
                        $('#raw_text_template').html(),
                        {"section_name": doc["section"]}
                    )
                );

                rawTextsContainer.appendChild(containerElement);
            }

            $(containerElement).find(".raw_text").text(
                doc["text"]
            )
            $(containerElement).find(".raw_text-confidence").text(
                doc["confidence"]
            );
            $(containerElement).find(".raw_text-time")
                .attr("datetime", formattedDates["iso_date"])
                .text(formattedDates["date_string"])
                .timeago()
                .timeago("updateFromDOM");
            break;
        case "output_text":
            var formattedDates = formatTimestamps(doc["timestamp"]);
            var rendered = Mustache.render(
                $('#output_text_template').html(),
                {
                    "output_text": doc["text"],
                    "iso_date": formattedDates["iso_date"],
                    "date_string": formattedDates["date_string"],
                    "section_name": doc["section"]
                }
            );

            var containerElement = document.createElement('div');
            containerElement.className = "output_text-container";

            $(containerElement).html(rendered);
            outputTextsContainer.insertBefore(containerElement, outputTextsContainer.firstChild);
            $(containerElement).find("time.timeago").timeago();

            if (outputTextsContainer.childNodes.length > 200) {
                outputTextsContainer.removeChild(outputTextsContainer.lastChild);
            }
        }
    }

    function formatTimestamps(timestamp) {
         var date = new Date(timestamp * 1000);
         return {
            "date_string": date.toISOString() + ' (' + date.toLocaleString() + ')',
            "iso_date": date.toISOString()
         };
    }

    function connect() {
        statusElement.textContent = "Connecting...";

        var socket = new WebSocket(
            (window.location.protocol == "https:" ? "wss://" : "ws://") +
            window.location.host + window.location.pathname + "api/events"
        );

        socket.onopen = function (event) {
            statusElement.textContent = "Connected";
            backoffCounter = 0;
        }
        socket.onmessage = handleMessage;
        socket.onerror = function (event) {
            statusElement.textContent = "Connection error";
            backoffCounter += 1;
            reconnect();
        }
        socket.onclose = function (event) {
            statusElement.textContent = "Disconnected";
            reconnect();
        }
    }

    function reconnect() {
        if (reconnectTimer) {
            return;
        }

        statusElement.textContent = "Waiting for reconnect...";

        var milliseconds = 5000 + backoffCounter * 10000;
        console.debug("Reconnect in ", milliseconds);

        reconnectTimer = window.setTimeout(function () {
            reconnectTimer = null;
            connect();
        }, milliseconds);
    }

    function loadRecent() {
        $.getJSON(
            "api/recent",
            "",
            function (data, textStatus, jqXHR) {
                $.each(data["recent_texts"], function (index, item) {
                    renderMessageDoc(item);
                });
            }
        );
    }

    Mustache.parse($('#output_text_template').html());

    loadRecent();
    connect();
}

$().ready(main);

