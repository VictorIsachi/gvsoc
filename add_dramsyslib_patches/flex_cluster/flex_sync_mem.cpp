/*
 * Copyright (C) 2024 ETH Zurich and University of Bologna
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * Author: Chi     Zhang , ETH Zurich (chizhang@iis.ee.ethz.ch)
 */

#include <vp/vp.hpp>
#include <vp/itf/io.hpp>
#include <vp/itf/wire.hpp>
#include <stdio.h>
#include <string.h>
#include <vector>
#include <list>
#include <queue>
#include <stdlib.h>
#include <stdint.h>
#include <cstdint>

class FlexSyncMem : public vp::Component
{

public:
    FlexSyncMem(vp::ComponentConf &config);

// private:
    static vp::IoReqStatus req(vp::Block *__this, vp::IoReq *req);

    vp::Trace           trace;
    vp::IoSlave         input_itf;
    uint32_t  			size;
    uint32_t            special_mem_base;
    uint8_t *    		sync_mem;

    // Needed to handle event modelling
    std::queue<vp::IoReq *>  denied_req_queue;  // Can also be vp::IoReq * denied_req to store a signle pending request
    vp::ClockEvent * atomic_rsp_event;  //  Event
    static void atomic_rsp_event_handler(vp::Block *__this, vp::ClockEvent *event); // Callback to be triggered on event
};

extern "C" vp::Component *gv_new(vp::ComponentConf &config)
{
    return new FlexSyncMem(config);
}

FlexSyncMem::FlexSyncMem(vp::ComponentConf &config)
    : vp::Component(config)
{
    //Initialize interface
    this->traces.new_trace("trace", &this->trace, vp::DEBUG);
    this->input_itf.set_req_meth(&FlexSyncMem::req);
    this->new_slave_port("input", &this->input_itf);
    
    //Initialize memory
    this->size = this->get_js_config()->get("size")->get_int();
    this->special_mem_base = this->get_js_config()->get("special_mem_base")->get_int();
    this->sync_mem = (uint8_t *)calloc(size, 1);
    if (this->sync_mem == NULL) throw std::bad_alloc();

    // Initialize event handling
    this->atomic_rsp_event = this->event_new(&FlexSyncMem::atomic_rsp_event_handler);   // Bind callback to event
    // In the case of a signle pending request initialize it to NULL (and put it to NULL each time you finished handling the event):
    // denied_req = NULL;
}

vp::IoReqStatus FlexSyncMem::req(vp::Block *__this, vp::IoReq *req)
{
    FlexSyncMem *_this = (FlexSyncMem *)__this;

    uint64_t offset = req->get_addr();
    uint64_t size = req->get_size();
    bool is_write = req->get_is_write();
    uint32_t *data = (uint32_t *) req->get_data();

    // _this->trace.msg("[FlexSyncMem] access (offset: 0x%x, size: 0x%x, is_write: %d)\n", offset, size, is_write);

    uint32_t * mem_ptr = (uint32_t *)(_this->sync_mem + offset);
    if (offset >= _this->special_mem_base)
    {
        // _this->trace.fatal("[FlexSyncMem] access special memory region\n");
        if ((is_write == 1))
        {
            if (*data == 0)
            {
                *mem_ptr = 0;
                _this->trace.msg("[FlexSyncMem] reset speical barrier at 0x%x\n", offset);
            } else {
                *mem_ptr = (*mem_ptr) + 1;
                _this->trace.msg("[FlexSyncMem] amo add speical barrier at 0x%x\n", offset);
            }
        } else {
            _this->trace.msg("[FlexSyncMem] check speical barrier at 0x%x\n", offset);
            data[0] = *mem_ptr;
        }
    } else {
        if ((is_write == 1))
        {
           *mem_ptr = 0;
           _this->trace.msg("[FlexSyncMem] amo reset\n");
        } else {
           data[0] = *mem_ptr;
           *mem_ptr = (*mem_ptr) + 1;
           _this->trace.msg("[FlexSyncMem] amo fetch and add\n");
           if(_this->denied_req_queue.size() == 0){
                _this->event_enqueue(_this->atomic_rsp_event, 10); // Enqueue event after 10 cycles
           }
           _this->denied_req_queue.push(req);   // Store request (need to do this so it does not get overwritten)
           return vp::IO_REQ_DENIED;    // Stall sender (OK - accepted; PENDING - handshake but no ack; DENIED - no handshake (stalls source); ERROR - error)
        }
    }

    return vp::IO_REQ_OK;
}

// Event handler
void FlexSyncMem::atomic_rsp_event_handler(vp::Block *__this, vp::ClockEvent *event) {
    FlexSyncMem *_this = (FlexSyncMem *)__this;

    vp::IoReq *req = _this->denied_req_queue.front();
    req->get_resp_port()->grant(req);   // Handshake
    req->get_resp_port()->resp(req);    // Response/ack
    _this->denied_req_queue.pop();

    if(_this->denied_req_queue.size() != 0){
        _this->event_enqueue(_this->atomic_rsp_event, 10);
    }
}

